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

sys.path.insert(0, str(ROOT_DIR))
from ledger_io import append_history
from fitness_math import MIN_SAMPLES_GENE_POOL, fitness_score

COMMUNITY_DIR = ROOT_DIR / "community" / "fitness"

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

def load_community_fitness() -> tuple[dict, dict]:
    """
    Agrega os exports anônimos de community/fitness/*.json (schema rdf-fitness/1).
    Retorna (model -> {ok, fail}, ruleset -> {ok, fail}) somando tarefas e duelos
    de TODOS os squads que contribuíram — a evolução vira global sem que nenhum
    dado de projeto saia da máquina de ninguém.
    """
    models: dict[str, dict] = {}
    rulesets: dict[str, dict] = {}
    if not COMMUNITY_DIR.exists():
        return models, rulesets
    for f in sorted(COMMUNITY_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("schema") != "rdf-fitness/1":
            continue
        for section, store in (("models", models), ("rulesets", rulesets)):
            for key, b in data.get(section, {}).items():
                agg = store.setdefault(key, {"ok": 0, "fail": 0})
                agg["ok"]   += int(b.get("tasks_ok", 0) or 0)
                agg["fail"] += int(b.get("tasks_fail", 0) or 0)
                duel_runs = int(b.get("duel_runs", 0) or 0)
                duel_ok   = int(b.get("duel_ok", 0) or 0)
                agg["ok"]   += duel_ok
                agg["fail"] += max(0, duel_runs - duel_ok)
    return models, rulesets


def select_best_genes(agents: list[dict]) -> tuple[str, str]:
    """
    Seleciona modelo + ruleset por EVIDÊNCIA, não por média ingênua:
      - combina contagens locais (tasks_completed/failed dos agentes) com o
        fitness agregado da comunidade (community/fitness/);
      - só considera genes com amostra mínima (MIN_SAMPLES_GENE_POOL);
      - ranqueia pelo limite inferior de Wilson (fitness_score), que penaliza
        pouca evidência: 2/2 (100%) perde de 190/200 (95%).
    Fallback: sem nenhum gene qualificado, usa o melhor disponível por Wilson
    mesmo abaixo da amostra mínima; sem dado nenhum, defaults universais.
    """
    model_ev, ruleset_ev = load_community_fitness()

    for agent in agents:
        ok   = int(agent.get("tasks_completed", 0) or 0)
        fail = int(agent.get("tasks_failed", 0) or 0)
        if model := agent.get("model"):
            b = model_ev.setdefault(model, {"ok": 0, "fail": 0})
            b["ok"] += ok
            b["fail"] += fail
        if rs := agent.get("ruleset_version"):
            b = ruleset_ev.setdefault(rs, {"ok": 0, "fail": 0})
            b["ok"] += ok
            b["fail"] += fail

    def best(evidence: dict, default: str) -> tuple[str, float, int, bool]:
        scored = [(key, fitness_score(b["ok"], b["ok"] + b["fail"]), b["ok"] + b["fail"])
                  for key, b in evidence.items() if (b["ok"] + b["fail"]) > 0]
        if not scored:
            return default, 0.0, 0, False
        qualified = [s for s in scored if s[2] >= MIN_SAMPLES_GENE_POOL]
        pool = qualified or scored
        key, score, n = max(pool, key=lambda s: s[1])
        return key, score, n, bool(qualified)

    best_model, m_score, m_n, m_q = best(model_ev, "google/gemini-2.5-flash")
    best_ruleset, r_score, r_n, r_q = best(ruleset_ev, "v1")

    print(f"  [FITNESS] modelo  : {best_model} (Wilson={m_score}, n={m_n}"
          + ("" if m_q else f", ABAIXO da amostra minima de {MIN_SAMPLES_GENE_POOL}") + ")")
    print(f"  [FITNESS] ruleset : {best_ruleset} (Wilson={r_score}, n={r_n}"
          + ("" if r_q else f", ABAIXO da amostra minima de {MIN_SAMPLES_GENE_POOL}") + ")")

    return best_model, best_ruleset

def write_ledger(entry: dict) -> None:
    ledger_path = LEDGER_DIR / "agent_ledger.log"
    if not ledger_path.parent.exists():
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def write_history(entry: dict) -> None:
    try:
        append_history(entry)
    except Exception as e:
        print(f"  [WARNING] Não foi possível escrever no histórico: {e}")

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

    # 2. Realiza crossover por evidência (local + community/fitness) ou usa overrides
    best_model, best_ruleset = select_best_genes(all_agents)
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
