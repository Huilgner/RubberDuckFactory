#!/usr/bin/env python3
"""
agents/agent_runner.py -- Runner de Agentes do Squad RubberDuckFactory

Modos:
  1. Hello-world (sem args):
       uv run python agents/agent_runner.py
       -> testa todos os agentes ativos com mensagem de apresentacao

  2. Tarefa especifica:
       uv run python agents/agent_runner.py --agent chen --task "..." [--project "Nome"]
       -> delega briefing a um agente, atualiza ledger e stats automaticamente

Pos-tarefa (modo 2):
  - tasks_completed / tasks_failed e success_rate atualizados no JSON do agente
  - Transicao de evolucao aplicada automaticamente se success_rate cruzar threshold
  - Entrada TAREFA_OK / TAREFA_FALHA gravada em project_ledger/agent_ledger.log
  - Entrada TASK_SUCCESS / TASK_FAILURE gravada em project_ledger/history.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 stdout to avoid cp1252 encoding errors on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from cost_tracker import record_cost

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------

ROOT_DIR   = Path(__file__).parent.parent
AGENTS_DIR = ROOT_DIR / "agents" / "active"
LEDGER_DIR = ROOT_DIR / "project_ledger"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

load_dotenv(ROOT_DIR / ".env")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

if not OPENROUTER_API_KEY:
    raise SystemExit(
        "OPENROUTER_API_KEY nao encontrada no .env\n"
        "Preencha o arquivo .env com: OPENROUTER_API_KEY=sk-or-v1-..."
    )

# Tokens maximos por modelo -- Gemini 2.5 Pro consome muitos tokens de raciocinio
MODEL_MAX_TOKENS: dict[str, int] = {
    "google/gemini-2.5-pro":           8000,
    "google/gemini-2.5-flash":         4000,
    "google/gemini-2.5-flash-lite":    2000,
    "deepseek/deepseek-chat":          4000,
    "deepseek/deepseek-v4-flash:free": 2000,
    "anthropic/claude-opus-4":         4000,
}
DEFAULT_MAX_TOKENS = 3000

TIER_NAMES = {1: "Observer", 2: "Operator", 3: "Specialist", 4: "Architect"}


# ---------------------------------------------------------------------------
# Carregamento de agentes
# ---------------------------------------------------------------------------

def load_agent(name: str) -> dict:
    """Carrega um agente pelo nome (case-insensitive). Levanta SystemExit se nao encontrado."""
    for path in AGENTS_DIR.glob("*.json"):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("nome", "").lower() == name.lower():
            d["_file"] = str(path)
            return d
    raise SystemExit(f"Agente '{name}' nao encontrado em {AGENTS_DIR}")


def load_all_agents() -> list[dict]:
    """Carrega todos os agentes ativos."""
    agents = []
    for path in sorted(AGENTS_DIR.glob("*.json")):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            d["_file"] = str(path)
            agents.append(d)
        except Exception:
            pass
    return agents


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

def build_system_prompt(agent: dict) -> str:
    """
    Gera system prompt a partir dos campos do JSON do agente.
    Aceita override completo via campo 'system_prompt' no JSON.
    """
    if "system_prompt" in agent:
        return agent["system_prompt"]

    nome      = agent.get("nome", "Agent")
    tier      = agent.get("tier", 1)
    specialty = agent.get("specialty", "General")
    model     = agent.get("model", "unknown")
    ruleset   = agent.get("ruleset_version", "v1")
    evolution = agent.get("evolution", "Stable")
    sr        = agent.get("success_rate", 100)
    tier_name = TIER_NAMES.get(tier, "Agent")

    return (
        f"You are {nome}, a Tier {tier} {tier_name} ({specialty}) "
        f"in the RubberDuckFactory AI agent squad.\n"
        f"Model: {model} | Ruleset: {ruleset} | Evolution: {evolution} | Success rate: {sr}%\n\n"
        "Operating principles:\n"
        "- Deliver precise, production-ready work within your specialty\n"
        "- Respond directly to the task -- no preamble, no filler\n"
        "- Be complete but concise; code must be correct and runnable\n"
        "- Flag ambiguities clearly rather than guessing\n"
        "- Follow existing patterns and conventions of the codebase\n\n"
        "You report to the Orchestrator (Claude). "
        "Your output will be reviewed before integration."
    )


# ---------------------------------------------------------------------------
# Chamada a API
# ---------------------------------------------------------------------------

def call_agent(agent: dict, user_message: str, max_tokens: int | None = None) -> dict:
    """
    Chama o agente via OpenRouter.
    Retorna: {content, finish_reason, prompt_tokens, completion_tokens, success, error}
    """
    model      = agent.get("model", "deepseek/deepseek-chat")
    system_msg = build_system_prompt(agent)

    if max_tokens is None:
        max_tokens = MODEL_MAX_TOKENS.get(model, DEFAULT_MAX_TOKENS)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://github.com/Huilgner/RubberDuckFactory",
        "X-Title":       "RubberDuckFactory",
    }
    payload = {
        "model":    model,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_message},
        ],
        "temperature": 0.3,
        "max_tokens":  max_tokens,
    }

    try:
        with httpx.Client(timeout=180.0) as client:
            resp = client.post(OPENROUTER_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data  = resp.json()
            usage = data.get("usage", {})
            return {
                "content":           (data["choices"][0]["message"]["content"] or "").strip(),
                "finish_reason":     data["choices"][0].get("finish_reason", "?"),
                "prompt_tokens":     usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "success":           True,
                "error":             None,
            }
    except httpx.HTTPStatusError as e:
        return {
            "content": "", "finish_reason": "error",
            "prompt_tokens": 0, "completion_tokens": 0,
            "success": False,
            "error": f"HTTP {e.response.status_code}: {e.response.text[:300]}",
        }
    except Exception as e:
        return {
            "content": "", "finish_reason": "error",
            "prompt_tokens": 0, "completion_tokens": 0,
            "success": False, "error": str(e),
        }


# ---------------------------------------------------------------------------
# Atualizacao de stats e evolucao do agente
# ---------------------------------------------------------------------------

def _compute_evolution(sr: float) -> str:
    if sr >= 85.0:
        return "Stable"
    elif sr >= 70.0:
        return "Mutating"
    return "Degraded"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_ledger(entry: dict) -> None:
    ledger = LEDGER_DIR / "agent_ledger.log"
    if not ledger.exists():
        return
    with open(ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def update_agent_stats(agent: dict, technical_success: bool) -> dict:
    """
    Incrementa tasks_completed ou tasks_failed, recalcula success_rate,
    aplica transicao de evolucao se necessario. Retorna o dict atualizado.
    """
    file_path = Path(agent["_file"])
    d = json.loads(file_path.read_text(encoding="utf-8"))

    if technical_success:
        d["tasks_completed"] = d.get("tasks_completed", 0) + 1
    else:
        d["tasks_failed"] = d.get("tasks_failed", 0) + 1

    total = d.get("tasks_completed", 0) + d.get("tasks_failed", 0)
    if total > 0:
        d["success_rate"] = round(d["tasks_completed"] / total * 100, 1)

    # Transicao de evolucao automatica
    new_evolution = _compute_evolution(float(d.get("success_rate", 100)))
    old_evolution = d.get("evolution", "Stable")
    if new_evolution != old_evolution:
        d["evolution"] = new_evolution
        _append_ledger({
            "ts":           _ts(),
            "type":         "EVOLUCAO",
            "agent":        d.get("nome", "?"),
            "from":         old_evolution,
            "to":           new_evolution,
            "success_rate": d.get("success_rate"),
            "trigger":      "agent_runner_pos_tarefa",
        })
        print(f"[EVOLUCAO] {d.get('nome','?')}: {old_evolution} -> {new_evolution} "
              f"(sr={d.get('success_rate')}%)")

    file_path.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    return d


# ---------------------------------------------------------------------------
# Ledger e historico
# ---------------------------------------------------------------------------

def write_task_ledger(agent: dict, success: bool, task: str, project: str,
                      error: str = "") -> None:
    """Escreve TAREFA_OK ou TAREFA_FALHA no agent_ledger.log."""
    _append_ledger({
        "ts":      _ts(),
        "type":    "TAREFA_OK" if success else "TAREFA_FALHA",
        "agent":   agent.get("nome", "?"),
        "project": project or "n/a",
        "reason":  task[:120] if success else (error or task[:120]),
    })


def write_history(agent: dict, success: bool, task: str, error: str = "") -> None:
    """Escreve TASK_SUCCESS ou TASK_FAILURE no history.json."""
    history_file = LEDGER_DIR / "history.json"
    try:
        data = json.loads(history_file.read_text(encoding="utf-8"))
        if "logs" not in data:
            data["logs"] = []
        entry: dict = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "type":      "TASK_SUCCESS" if success else "TASK_FAILURE",
            "agent":     agent.get("nome", "?"),
            "task":      task[:200],
        }
        if not success and error:
            entry["reason"] = error[:200]
        data["logs"].append(entry)
        history_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"  [WARNING] Nao foi possivel gravar em history.json: {e}")


# ---------------------------------------------------------------------------
# Modos de execucao
# ---------------------------------------------------------------------------

def run_hello_world() -> None:
    """Modo legado: testa todos os agentes com mensagem de apresentacao."""
    print("=" * 60)
    print("  AGENT RUNNER -- RubberDuckFactory Squad")
    print("  Testando: nome + modelo + hello world de cada agente")
    print("=" * 60)
    print()

    agents = load_all_agents()
    if not agents:
        print("Nenhum agente encontrado em agents/active/")
        return

    for agent in agents:
        nome      = agent.get("nome", "?")
        model     = agent.get("model", "?")
        tier      = agent.get("tier", "?")
        evolution = agent.get("evolution", "Stable")

        print(f"{'-' * 60}")
        print(f"Agente: {nome} | Tier {tier} | {evolution} | {model}")
        print()

        msg = (
            f"Apresente-se em uma unica mensagem curta: seu nome ({nome}), "
            f"seu modelo ({model}) e um 'Hello World'."
        )
        resultado = call_agent(agent, msg, max_tokens=1000)
        record_cost(
            agent=nome, model=model, task="hello_world",
            prompt_tokens=resultado["prompt_tokens"],
            completion_tokens=resultado["completion_tokens"],
        )

        if resultado["success"]:
            print(f"  {resultado['content']}")
        else:
            print(f"  ERRO: {resultado['error']}")
        print(f"  Tokens: {resultado['prompt_tokens']} in / {resultado['completion_tokens']} out")
        print()

    print("=" * 60)
    print("Todos os agentes responderam.")
    print("=" * 60)


def run_task(agent_name: str, task: str, project: str) -> None:
    """Modo tarefa: delega briefing especifico a um agente e registra tudo."""
    agent     = load_agent(agent_name)
    nome      = agent.get("nome", "?")
    model     = agent.get("model", "?")
    tier      = agent.get("tier", "?")
    evolution = agent.get("evolution", "Stable")
    sr        = agent.get("success_rate", 100)

    # Agentes Degraded nao recebem tarefas
    if evolution == "Degraded":
        print(f"[BLOQUEADO] {nome} esta em estado Degraded.")
        print("  Nenhuma tarefa nova sem aprovacao explicita do Arquiteto.")
        sys.exit(1)

    print("=" * 60)
    print(f"  RubberDuckFactory -- Task Runner")
    print(f"  Agente  : {nome} (Tier {tier} | {evolution} | sr={sr}%)")
    print(f"  Modelo  : {model}")
    print(f"  Projeto : {project or 'n/a'}")
    print("=" * 60)
    print()
    print(f"BRIEFING:\n{task}")
    print()
    print(f"Chamando {nome}...")
    print()

    resultado = call_agent(agent, task)
    technical_success = resultado["success"]

    # Custo
    record_cost(
        agent=nome, model=model, task=task[:80],
        prompt_tokens=resultado["prompt_tokens"],
        completion_tokens=resultado["completion_tokens"],
    )

    # Stats, evolucao, ledger e historico
    updated = update_agent_stats(agent, technical_success)
    write_task_ledger(agent, technical_success, task, project, resultado.get("error") or "")
    write_history(agent, technical_success, task, resultado.get("error") or "")

    # Output
    if technical_success:
        print(f"RESPOSTA DE {nome.upper()}:")
        print("-" * 60)
        print(resultado["content"])
        print("-" * 60)
        new_sr  = updated.get("success_rate", sr)
        ok_cnt  = updated.get("tasks_completed", 0)
        fail_cnt = updated.get("tasks_failed", 0)
        print(
            f"Tokens: {resultado['prompt_tokens']} in / {resultado['completion_tokens']} out"
            f" | finish={resultado['finish_reason']}"
            f" | sr={new_sr}% ({ok_cnt}ok/{fail_cnt}fail)"
        )
    else:
        print(f"ERRO: {resultado['error']}")

    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="RubberDuckFactory Agent Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  uv run python agents/agent_runner.py\n"
            "  uv run python agents/agent_runner.py --agent chen --task 'Criar endpoint POST /items'\n"
            "  uv run python agents/agent_runner.py -a nova -t 'Refatorar Card' -p 'ClienteXYZ'\n"
        ),
    )
    parser.add_argument("--agent",   "-a", metavar="NOME",
                        help="Nome do agente (ex: chen, nova, shadow)")
    parser.add_argument("--task",    "-t", metavar="BRIEFING",
                        help="Briefing/tarefa para o agente")
    parser.add_argument("--project", "-p", metavar="PROJETO",
                        default="RubberDuckFactory",
                        help="Nome do projeto para o ledger (padrao: RubberDuckFactory)")

    args = parser.parse_args()

    if args.agent and args.task:
        run_task(args.agent, args.task, args.project)
    elif args.agent or args.task:
        parser.error("Use --agent e --task juntos, ou nenhum (modo hello-world).")
    else:
        run_hello_world()


if __name__ == "__main__":
    main()
