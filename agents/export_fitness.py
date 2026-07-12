#!/usr/bin/env python3
"""
agents/export_fitness.py -- Exportador de Fitness Anonimo (ADR-003 distribuido)

Gera um resumo agregado de fitness POR MODELO e POR RULESET a partir do
historico local, SEM nenhum texto de tarefa, nome de projeto ou conteudo:
apenas contagens, taxas de sucesso e custo. Seguro para versionar.

Fluxo de propagacao:
  1. Cada usuario roda:  python agents/export_fitness.py --user seu_nome
  2. O arquivo community/fitness/<user>.json e criado/atualizado
  3. Commit + PR -> o gene_crossover passa a enxergar a variancia de fitness
     de TODOS os squads, acelerando a selecao artificial sem compartilhar
     nenhum dado dos projetos de ninguem.

O que NUNCA sai daqui: texto de tarefas, nomes de projetos, conteudo de
respostas, caminhos de arquivos, blueprints, logs.
"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR   = Path(__file__).parent.parent
ACTIVE_DIR = ROOT_DIR / "agents" / "active"
OUT_DIR    = ROOT_DIR / "community" / "fitness"

sys.path.insert(0, str(ROOT_DIR))
from ledger_io import read_history

# Campos permitidos no export -- allowlist explicita, nada alem disso sai
SAFE_EVENT_TYPES = {"TASK_SUCCESS", "TASK_FAILURE", "INFRA_FAILURE", "COST_RECORD", "DUEL_RUN"}


def _default_user() -> str:
    try:
        r = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, timeout=5)
        name = r.stdout.strip()
        if name:
            return name.lower().replace(" ", "_")
    except Exception:
        pass
    return "anonimo"


def build_summary() -> dict:
    events = read_history()

    # agente -> (model, ruleset) atual, a partir do squad local
    agent_meta: dict[str, dict] = {}
    for p in ACTIVE_DIR.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            agent_meta[d.get("nome", "?")] = {
                "model":   d.get("model", "?"),
                "ruleset": d.get("ruleset_version", "v1"),
            }
        except Exception:
            pass

    models: dict[str, dict] = {}
    rulesets: dict[str, dict] = {}

    def bucket(store: dict, key: str) -> dict:
        return store.setdefault(key, {
            "tasks_ok": 0, "tasks_fail": 0, "infra_failures": 0,
            "duel_runs": 0, "duel_ok": 0,
            "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0,
        })

    for e in events:
        etype = e.get("type")
        if etype not in SAFE_EVENT_TYPES:
            continue

        if etype == "DUEL_RUN":
            for r in e.get("runs", []):
                b = bucket(models, r.get("model", "?"))
                b["duel_runs"] += 1
                if r.get("technical_success"):
                    b["duel_ok"] += 1
                b["prompt_tokens"]     += int(r.get("prompt_tokens", 0) or 0)
                b["completion_tokens"] += int(r.get("completion_tokens", 0) or 0)
                b["cost_usd"]          += float(r.get("cost_usd", 0.0) or 0.0)
            continue

        meta = agent_meta.get(e.get("agent", ""), None)
        if meta is None:
            continue  # agente desconhecido/sintetico: fora do agregado

        targets = [bucket(models, meta["model"]), bucket(rulesets, meta["ruleset"])]
        if etype == "TASK_SUCCESS":
            for b in targets:
                b["tasks_ok"] += 1
        elif etype == "TASK_FAILURE":
            for b in targets:
                b["tasks_fail"] += 1
        elif etype == "INFRA_FAILURE":
            for b in targets:
                b["infra_failures"] += 1
        elif etype == "COST_RECORD":
            tk = e.get("tokens", {})
            b = bucket(models, e.get("model", meta["model"]))
            b["prompt_tokens"]     += int(tk.get("prompt", 0) or 0)
            b["completion_tokens"] += int(tk.get("completion", 0) or 0)
            b["cost_usd"]          += float(e.get("cost_usd", 0.0) or 0.0)

    # taxas derivadas
    for store in (models, rulesets):
        for b in store.values():
            total = b["tasks_ok"] + b["tasks_fail"]
            b["success_rate"] = round(b["tasks_ok"] / total * 100, 1) if total else None
            duels = b["duel_runs"]
            b["duel_success_rate"] = round(b["duel_ok"] / duels * 100, 1) if duels else None
            b["cost_usd"] = round(b["cost_usd"], 6)

    return {
        "schema":       "rdf-fitness/1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "events_total": len(events),
        "models":       models,
        "rulesets":     rulesets,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Exporta fitness agregado e anonimo para community/fitness/")
    p.add_argument("--user", "-u", default=None, help="identificador do arquivo (padrao: git user.name)")
    p.add_argument("--dry-run", action="store_true", help="imprime o resumo sem gravar")
    args = p.parse_args()

    user = (args.user or _default_user()).lower().replace(" ", "_")
    summary = build_summary()
    summary["user"] = user

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.dry_run:
        print("\n[DRY-RUN] nada gravado.")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{user}.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] Fitness exportado -> {out}")
    print("Revise o conteudo acima (so agregados) e faca commit/PR para compartilhar.")


if __name__ == "__main__":
    main()
