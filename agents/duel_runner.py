#!/usr/bin/env python3
"""
agents/duel_runner.py -- Orquestrador de Duelos de Agentes (ADR-003)

O Orquestrador decide, POR TAREFA, como os agentes de um mesmo papel competem:

  * solo (alternado)  -> tarefas simples: roda UM agente, alternando champion/
                         challenger a cada chamada. Testa com frequencia e baixo custo.
  * parallel          -> tarefas complexas: roda TODOS em paralelo na mesma tarefa.
                         Expoe divergencias -> facil achar erros/alucinacoes.

Cada execucao grava custo (cost_tracker) + um resumo DUEL_RUN no history.json e
atualiza success_rate/evolution dos agentes -> dados de fitness por modelo para o
gene_crossover (ADR-003) evoluir agentes atuais e futuros.

Uso:
  uv run python agents/duel_runner.py --role frontend --task "..."            # auto
  uv run python agents/duel_runner.py --role frontend --task "..." --mode parallel
  uv run python agents/duel_runner.py --role frontend --task "..." --mode solo
  uv run python agents/duel_runner.py --role frontend --task "..." --complexity complex
  uv run python agents/duel_runner.py --role frontend --task "..." --judge       # juiz barato escolhe vencedor
  uv run python agents/duel_runner.py --role frontend --task "..." --no-stats     # nao mexe nos JSONs dos agentes
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))          # agent_runner
sys.path.insert(0, str(Path(__file__).parent.parent))   # cost_tracker

from agent_runner import (
    load_agent, call_agent, update_agent_stats,
    write_task_ledger, write_history,
)
from cost_tracker import record_cost, calculate_cost

ROOT_DIR   = Path(__file__).parent.parent
LEDGER_DIR = ROOT_DIR / "project_ledger"
ROSTER     = Path(__file__).parent / "duel_roster.json"
STATE      = LEDGER_DIR / "duel_state.json"
DUELS_DIR  = LEDGER_DIR / "duels"

JUDGE_MODEL = "deepseek/deepseek-chat"  # barato; usado so com --judge

COMPLEX_KEYWORDS = [
    "complex", "arquitet", "refator", "integr", "seguran", "security",
    "performance", "escal", "migrar", "otimiz", "concorr", "distribu",
    "multiplo", "multiple", "pipeline", "infra", "deploy", "autentic", "auth",
]


# --------------------------------------------------------------------------- #
# Estado de rotacao (para o modo solo alternado)
# --------------------------------------------------------------------------- #
def _load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


# --------------------------------------------------------------------------- #
# Roster: champion + challengers do papel
# --------------------------------------------------------------------------- #
def load_roster(role: str) -> list[dict]:
    data = json.loads(ROSTER.read_text(encoding="utf-8"))
    entry = data.get("roles", {}).get(role.lower())
    if not entry:
        raise SystemExit(f"Papel '{role}' nao encontrado em duel_roster.json. "
                         f"Papeis: {list(data.get('roles', {}).keys())}")
    names = [entry["champion"]] + list(entry.get("challengers", []))
    agents = [load_agent(n) for n in names]
    for a, n in zip(agents, names):
        a["_roster_name"] = n
    return agents


# --------------------------------------------------------------------------- #
# Decisao de complexidade / modo
# --------------------------------------------------------------------------- #
def assess_complexity(task: str) -> tuple[str, list[str]]:
    t = task.lower()
    reasons = []
    score = 0
    if len(task) > 600:
        score += 2; reasons.append("tarefa longa (>600 chars)")
    elif len(task) > 280:
        score += 1; reasons.append("tarefa media (>280 chars)")
    hits = [k for k in COMPLEX_KEYWORDS if k in t]
    if hits:
        score += len(hits); reasons.append(f"palavras-chave: {', '.join(hits[:5])}")
    bullets = t.count("\n-") + t.count("\n*") + t.count("\n1.")
    if bullets >= 3:
        score += 1; reasons.append(f"multiplos requisitos ({bullets})")
    return ("complex" if score >= 3 else "simple"), reasons


def decide(task: str, mode: str, complexity: str) -> tuple[str, str, list[str]]:
    """Retorna (mode_final, complexity_final, motivos)."""
    if complexity == "auto":
        complexity, reasons = assess_complexity(task)
    else:
        reasons = [f"complexidade forcada: {complexity}"]
    if mode == "auto":
        mode = "parallel" if complexity == "complex" else "solo"
    return mode, complexity, reasons


# --------------------------------------------------------------------------- #
# Execucao de um agente + sinais de qualidade
# --------------------------------------------------------------------------- #
def run_one(agent: dict, task: str, record_stats: bool) -> dict:
    name  = agent.get("nome", "?")
    model = agent.get("model", "?")
    res = call_agent(agent, task)
    content = res.get("content", "") or ""
    pin, pout = res.get("prompt_tokens", 0), res.get("completion_tokens", 0)
    truncated = res.get("finish_reason") == "length"
    # Heuristica de sucesso tecnico: respondeu, nao vazio, nao truncado
    technical_success = bool(res.get("success")) and len(content.strip()) >= 40 and not truncated
    cost = calculate_cost(model, pin, pout)

    if record_stats and res.get("success"):
        record_cost(name, model, task[:120], pin, pout)
        update_agent_stats(agent, technical_success)
        write_task_ledger(agent, technical_success, task, "duel")
        write_history(agent, technical_success, task,
                      "" if technical_success else (res.get("error") or "saida incompleta"))

    return {
        "agent": name, "model": model,
        "success": res.get("success"), "technical_success": technical_success,
        "truncated": truncated, "finish_reason": res.get("finish_reason"),
        "chars": len(content), "prompt_tokens": pin, "completion_tokens": pout,
        "cost_usd": cost, "error": res.get("error"), "content": content,
    }


def divergence(a: str, b: str) -> dict:
    wa, wb = set(a.lower().split()), set(b.lower().split())
    inter = len(wa & wb); union = len(wa | wb) or 1
    return {
        "jaccard": round(inter / union, 3),
        "len_delta_pct": round(abs(len(a) - len(b)) / (max(len(a), len(b)) or 1) * 100, 1),
    }


def judge_outputs(task: str, runs: list[dict]) -> dict:
    """Juiz barato escolhe o melhor output (so com --judge)."""
    judge = {"nome": "Judge", "model": JUDGE_MODEL,
             "system_prompt": "Voce e um avaliador imparcial de qualidade de codigo/entregas. "
                              "Responda SOMENTE JSON."}
    blocks = "\n\n".join(
        f"### CANDIDATO {i+1} (agente {r['agent']}, modelo {r['model']})\n{r['content'][:4000]}"
        for i, r in enumerate(runs)
    )
    prompt = (f"Tarefa:\n{task}\n\n{blocks}\n\n"
              f'Avalie corretude, completude e ausencia de alucinacao. Responda JSON: '
              f'{{"winner": <numero 1..{len(runs)}>, "scores": [n1,...], "motivo": "..."}}')
    res = call_agent(judge, prompt, max_tokens=500)
    try:
        txt = res["content"]
        txt = txt[txt.find("{"): txt.rfind("}") + 1]
        return json.loads(txt)
    except Exception as e:
        return {"winner": None, "scores": [], "motivo": f"juiz falhou: {e}"}


# --------------------------------------------------------------------------- #
# Modos
# --------------------------------------------------------------------------- #
def run_solo(agents: list[dict], role: str, task: str, record_stats: bool) -> list[dict]:
    state = _load_state()
    idx = state.get(role.lower(), 0) % len(agents)
    chosen = agents[idx]
    if record_stats:
        state[role.lower()] = (idx + 1) % len(agents)
        _save_state(state)
    print(f"  modo SOLO -> alternancia escolheu: {chosen['nome']} ({chosen['model']}) "
          f"[proximo: {agents[(idx+1) % len(agents)]['nome']}]")
    return [run_one(chosen, task, record_stats)]


def run_parallel(agents: list[dict], task: str, record_stats: bool) -> list[dict]:
    print(f"  modo PARALLEL -> {', '.join(a['nome'] for a in agents)} na mesma tarefa")
    return [run_one(a, task, record_stats) for a in agents]


# --------------------------------------------------------------------------- #
# Persistencia de artefatos + resumo
# --------------------------------------------------------------------------- #
def persist(role: str, mode: str, complexity: str, task: str,
            runs: list[dict], verdict: dict | None) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = DUELS_DIR / f"{role}_{stamp}"
    d.mkdir(parents=True, exist_ok=True)
    for r in runs:
        (d / f"{r['agent']}.txt").write_text(r["content"], encoding="utf-8")
    summary = {
        "timestamp": _ts(), "type": "DUEL_RUN", "role": role, "mode": mode,
        "complexity": complexity, "task": task[:300],
        "runs": [{k: v for k, v in r.items() if k != "content"} for r in runs],
        "verdict": verdict,
    }
    (d / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    # tambem no history.json (alimenta ADR-003)
    hf = LEDGER_DIR / "history.json"
    try:
        data = json.loads(hf.read_text(encoding="utf-8"))
        data.setdefault("logs", []).append(summary)
        hf.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"  [WARNING] history.json: {e}")
    return d


def print_report(runs: list[dict], mode: str, verdict: dict | None) -> None:
    print("\n" + "=" * 64)
    print(f"  {'AGENTE':10} {'MODELO':28} {'OK':3} {'TRUNC':5} {'TOKENS':>10} {'USD':>12}")
    print("-" * 64)
    for r in runs:
        ok = "ok" if r["technical_success"] else "x"
        tok = f"{r['prompt_tokens']}/{r['completion_tokens']}"
        print(f"  {r['agent']:10} {r['model'][:28]:28} {ok:3} "
              f"{('sim' if r['truncated'] else '-'):5} {tok:>10} ${r['cost_usd']:.6f}")
    if mode == "parallel" and len(runs) == 2:
        dv = divergence(runs[0]["content"], runs[1]["content"])
        flag = "  <-- ALTA DIVERGENCIA (verificar alucinacao)" if dv["jaccard"] < 0.4 else ""
        print("-" * 64)
        print(f"  divergencia: jaccard={dv['jaccard']} | dif. tamanho={dv['len_delta_pct']}%{flag}")
        cheap = min(runs, key=lambda r: r["cost_usd"])
        exp   = max(runs, key=lambda r: r["cost_usd"])
        if exp["cost_usd"] > 0:
            print(f"  custo: {cheap['agent']} foi {exp['cost_usd']/max(cheap['cost_usd'],1e-9):.1f}x "
                  f"mais barato que {exp['agent']}")
    if verdict:
        print("-" * 64)
        print(f"  JUIZ -> vencedor: candidato {verdict.get('winner')} | scores={verdict.get('scores')}")
        print(f"          motivo: {verdict.get('motivo','')[:200]}")
    print("=" * 64)


# --------------------------------------------------------------------------- #
def main() -> None:
    p = argparse.ArgumentParser(description="Orquestrador de Duelos de Agentes (ADR-003)")
    p.add_argument("--role", "-r", required=True, help="Papel (ex: frontend)")
    p.add_argument("--task", "-t", required=True, help="Tarefa/briefing")
    p.add_argument("--mode", choices=["auto", "solo", "parallel"], default="auto")
    p.add_argument("--complexity", choices=["auto", "simple", "complex"], default="auto")
    p.add_argument("--judge", action="store_true", help="Juiz barato escolhe vencedor (parallel)")
    p.add_argument("--no-stats", action="store_true", help="Nao grava custo/stats/ledger (teste seco)")
    args = p.parse_args()

    agents = load_roster(args.role)
    mode, complexity, reasons = decide(args.task, args.mode, args.complexity)
    record_stats = not args.no_stats

    roster_str = ", ".join("{}({})".format(a["nome"], a["model"]) for a in agents)
    print("=" * 64)
    print(f"  ORQUESTRADOR DE DUELOS — papel: {args.role}")
    print(f"  Roster: {roster_str}")
    print(f"  Decisao: complexidade={complexity} -> modo={mode}"
          + ("  [stats OFF]" if not record_stats else ""))
    print(f"  Motivos: {'; '.join(reasons) or 'n/a'}")
    print("=" * 64)

    if mode == "solo":
        runs = run_solo(agents, args.role, args.task, record_stats)
        verdict = None
    else:
        runs = run_parallel(agents, args.task, record_stats)
        verdict = judge_outputs(args.task, runs) if (args.judge and len(runs) >= 2) else None

    out_dir = persist(args.role, mode, complexity, args.task, runs, verdict) if record_stats else None
    print_report(runs, mode, verdict)
    if out_dir:
        print(f"  artefatos: {out_dir}")


if __name__ == "__main__":
    main()
