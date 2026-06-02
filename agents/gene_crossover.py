#!/usr/bin/env python3
"""
agents/gene_crossover.py -- Mecanismo de Seleção Artificial de Agentes (Gene Pool / ADR-003)
"""

import sys

# Force UTF-8 stdout to avoid cp1252 encoding errors on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR   = Path(__file__).parent.parent
AGENTS_DIR = ROOT_DIR / "agents" / "active"
LEDGER_DIR = ROOT_DIR / "project_ledger"

def load_all_agents() -> list[dict]:
    """Carrega todos os agentes ativos."""
    agents = []
    for path in AGENTS_DIR.glob("*.json"):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            d["_file"] = str(path)
            agents.append(d)
        except Exception:
            pass
    return agents

def get_gene_pool(agents: list[dict]) -> list[dict]:
    """Filtra apenas agentes saudáveis (Stable com bom success_rate) para a piscina genética."""
    pool = [a for a in agents if a.get("evolution") == "Stable" and a.get("success_rate", 0) >= 85.0]
    # Se a piscina estiver vazia, pega qualquer agente ativo para não travar o crossover
    if not pool:
        pool = [a for a in agents if a.get("status") == "active"]
    return pool

def select_best_genes(pool: list[dict]) -> tuple[str, str]:
    """Seleciona as melhores configurações (modelo + ruleset) a partir do pool genético."""
    if not pool:
        # Fallbacks universais caso não haja agentes
        return "google/gemini-2.5-flash", "v1"

    # Seleciona o melhor modelo com base na maior taxa de sucesso média dos agentes que o utilizam
    model_stats = {}
    for agent in pool:
        model = agent.get("model")
        sr = agent.get("success_rate", 0.0)
        if model:
            stats = model_stats.setdefault(model, [])
            stats.append(sr)

    best_model = max(model_stats.keys(), key=lambda m: sum(model_stats[m])/len(model_stats[m]))

    # Seleciona a melhor versão de ruleset com base no maior success_rate médio
    ruleset_stats = {}
    for agent in pool:
        rs = agent.get("ruleset_version")
        sr = agent.get("success_rate", 0.0)
        if rs:
            stats = ruleset_stats.setdefault(rs, [])
            stats.append(sr)

    best_ruleset = max(ruleset_stats.keys(), key=lambda r: sum(ruleset_stats[r])/len(ruleset_stats[r]))

    return best_model, best_ruleset

def write_ledger(entry: dict) -> None:
    ledger_path = LEDGER_DIR / "agent_ledger.log"
    if not ledger_path.parent.exists():
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def write_history(entry: dict) -> None:
    history_file = LEDGER_DIR / "history.json"
    if not history_file.exists():
        return
    try:
        data = json.loads(history_file.read_text(encoding="utf-8"))
        data.setdefault("logs", []).append(entry)
        history_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"  [WARNING] Não foi possível escrever no history.json: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Mecanismo de Seleção Artificial de Agentes (ADR-003)",
        epilog="Exemplo: uv run python agents/gene_crossover.py --name Neo --specialty 'Code Refactoring'"
    )
    parser.add_argument("--name", "-n", required=True, help="Nome do agente a ser criado ou evoluído")
    parser.add_argument("--specialty", "-s", required=True, help="Especialidade do agente")
    parser.add_argument("--tier", "-t", type=int, default=2, choices=[1, 2, 3, 4], help="Tier clearance do agente (padrão: 2)")
    parser.add_argument("--model", metavar="LLM", help="Forçar modelo específico (ignora crossover)")
    parser.add_argument("--ruleset", metavar="VERSION", help="Forçar ruleset específico (ignora crossover)")

    args = parser.parse_args()

    print("=" * 60)
    print("🧬  RubberDuckFactory -- Gene Pool Selection & Crossover (ADR-003)")
    print("=" * 60)

    # 1. Carrega todos os agentes
    all_agents = load_all_agents()
    pool = get_gene_pool(all_agents)

    print(f"Squad atual: {len(all_agents)} agentes.")
    print(f"Piscina Genética de Alto Fitness (Stable & sr >= 85%): {[a.get('nome') for a in pool]}")

    # 2. Realiza crossover ou usa overrides
    best_model, best_ruleset = select_best_genes(pool)
    final_model = args.model if args.model else best_model
    final_ruleset = args.ruleset if args.ruleset else best_ruleset

    print(f"\n[CROSSOVER RESULTS]")
    print(f"  -> Gene de Modelo herdado: {final_model}" + (" (override)" if args.model else " (crossover)"))
    print(f"  -> Gene de Ruleset herdado: {final_ruleset}" + (" (override)" if args.ruleset else " (crossover)"))

    # 3. Prepara o JSON do novo agente
    agent_filename = f"{args.name.lower()}.json"
    agent_path = AGENTS_DIR / agent_filename

    is_update = agent_path.exists()
    action_str = "EVOLVED" if is_update else "SPAWNED"

    agent_data = {
        "nome": args.name,
        "tier": args.tier,
        "specialty": args.specialty,
        "model": final_model,
        "ruleset_version": final_ruleset,
        "evolution": "Stable",
        "success_rate": 100.0,
        "status": "active",
        "pontos": {
            "externos": 0,
            "internos": 0
        },
        "tasks_completed": 0,
        "tasks_failed": 0,
        "_audit_note": f"Gene selection ({action_str}) em {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
    }

    # Se for um update de agente existente, preserva pontos e histórico de tarefas
    if is_update:
        try:
            old_data = json.loads(agent_path.read_text(encoding="utf-8"))
            agent_data["pontos"] = old_data.get("pontos", {"externos": 0, "internos": 0})
            agent_data["tasks_completed"] = old_data.get("tasks_completed", 0)
            agent_data["tasks_failed"] = old_data.get("tasks_failed", 0)
            # recalcula success rate se tiver tarefas
            total = agent_data["tasks_completed"] + agent_data["tasks_failed"]
            if total > 0:
                agent_data["success_rate"] = round(agent_data["tasks_completed"] / total * 100, 1)
        except Exception:
            pass

    # Grava o arquivo JSON
    agent_path.write_text(json.dumps(agent_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Agente {args.name} gravado com sucesso em {agent_path}")

    # Registra no log de governança
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    write_ledger({
        "ts": ts,
        "type": "EVOLUCAO",
        "agent": args.name,
        "from": "n/a" if not is_update else "Previous_Config",
        "to": "Stable",
        "success_rate": agent_data["success_rate"],
        "trigger": f"gene_crossover_{action_str.lower()}"
    })

    write_history({
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "type": "TASK_SUCCESS",
        "agent": "Orchestrator",
        "task": f"Spawn/Evolve agent {args.name} with model {final_model} and ruleset {final_ruleset} via gene selection."
    })

    print("=" * 60)

if __name__ == "__main__":
    main()
