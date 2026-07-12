#!/usr/bin/env python3
"""
agents/inter_agent_negotiation.py -- Canal de Comunicação e Negociação Interagentes
"""

import sys

# Force UTF-8 stdout to avoid cp1252 encoding errors on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from agent_runner import load_agent, call_agent

ROOT_DIR = Path(__file__).parent.parent
LEDGER_DIR = ROOT_DIR / "project_ledger"
BLACKBOARD_FILE = LEDGER_DIR / "negotiation_blackboard.json"

sys.path.insert(0, str(ROOT_DIR))
from ledger_io import append_history

def write_history(entry: dict) -> None:
    try:
        append_history(entry)
    except Exception as e:
        print(f"  [WARNING] Não foi possível escrever no histórico: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Canal de Comunicação e Negociação Interagentes",
        epilog="Exemplo: uv run python agents/inter_agent_negotiation.py --agent1 chen --agent2 nova --topic 'Definir payload do POST /api/tasks' --turns 2"
    )
    parser.add_argument("--agent1", "-a1", required=True, help="Nome do primeiro agente (ex: chen)")
    parser.add_argument("--agent2", "-a2", required=True, help="Nome do segundo agente (ex: nova)")
    parser.add_argument("--topic", "-t", required=True, help="Tópico/problema a ser negociado")
    parser.add_argument("--turns", type=int, default=2, help="Número de turnos de negociação (padrão: 2)")

    args = parser.parse_args()

    print("=" * 60)
    print("🤝  RubberDuckFactory -- Inter-Agent Negotiation Channel")
    print("=" * 60)
    print(f"Agente 1 : {args.agent1.upper()}")
    print(f"Agente 2 : {args.agent2.upper()}")
    print(f"Tópico   : {args.topic}")
    print(f"Turnos   : {args.turns}")
    print("=" * 60)

    # 1. Carrega os agentes
    a1 = load_agent(args.agent1)
    a2 = load_agent(args.agent2)

    # 2. Loop de negociação
    negotiation_log = []

    print("\n[INICIANDO NEGOCIAÇÃO]")

    for turn in range(1, args.turns + 1):
        print(f"\n--- Turno {turn} de {args.turns} ---")

        # --- Turno do Agente 1 ---
        history_str = "\n".join([f"{m['author']}: {m['content']}" for m in negotiation_log])
        prompt_1 = (
            f"You are participating in a technical negotiation with {a2['nome']}.\n"
            f"Topic: {args.topic}\n\n"
            f"Chat History:\n{history_str if history_str else '(No messages yet)'}\n\n"
            f"It is your turn. Please write a concise proposal or response. Focus strictly on technical tradeoffs. "
            f"Propose clear structures/solutions. Be extremely direct -- no preamble, no fluff."
        )
        print(f"Chamando {a1['nome']}...")
        res1 = call_agent(a1, prompt_1)
        if not res1["success"]:
            print(f"❌ Erro ao chamar {a1['nome']}: {res1['error']}")
            sys.exit(1)

        msg1 = res1["content"]
        print(f"\n[{a1['nome'].upper()}]:")
        print(msg1)
        negotiation_log.append({"turn": turn, "author": a1["nome"], "content": msg1})

        # --- Turno do Agente 2 ---
        history_str = "\n".join([f"{m['author']}: {m['content']}" for m in negotiation_log])
        prompt_2 = (
            f"You are participating in a technical negotiation with {a1['nome']}.\n"
            f"Topic: {args.topic}\n\n"
            f"Chat History:\n{history_str}\n\n"
            f"It is your turn. Read {a1['nome']}'s proposal carefully. Write a concise counter-proposal, critique, or agreement. "
            f"Propose technical solutions. Be extremely direct -- no preamble, no fluff."
        )
        print(f"\nChamando {a2['nome']}...")
        res2 = call_agent(a2, prompt_2)
        if not res2["success"]:
            print(f"❌ Erro ao chamar {a2['nome']}: {res2['error']}")
            sys.exit(1)

        msg2 = res2["content"]
        print(f"\n[{a2['nome'].upper()}]:")
        print(msg2)
        negotiation_log.append({"turn": turn, "author": a2["nome"], "content": msg2})

    # 3. Consolidação final (Consensus Extraction)
    print("\n" + "=" * 60)
    print("📝  RubberDuckFactory -- Salvando Consenso no Blackboard")
    print("=" * 60)

    blackboard_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "topic": args.topic,
        "participants": [a1["nome"], a2["nome"]],
        "turns": args.turns,
        "negotiation_log": negotiation_log,
        "consensus_proposal": negotiation_log[-1]["content"] if negotiation_log else ""
    }

    # Grava o blackboard
    if not LEDGER_DIR.exists():
        LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    BLACKBOARD_FILE.write_text(json.dumps(blackboard_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Resultados de negociação gravados em {BLACKBOARD_FILE}")

    # Registra no histórico geral
    write_history({
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "type": "TASK_SUCCESS",
        "agent": "Orchestrator",
        "task": f"Inter-agent negotiation completed between {a1['nome']} and {a2['nome']} on topic: '{args.topic[:100]}'."
    })
    print("=" * 60)

if __name__ == "__main__":
    main()
