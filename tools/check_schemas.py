#!/usr/bin/env python3
"""
tools/check_schemas.py — Validação de CI para os artefatos compartilhados do RDF.

1. agents/pool/*.json  — definições do pool global: campos obrigatórios,
   tier em [1..4], stats NEUTRAS (o pool nunca carrega fenótipo de ninguém).
2. community/fitness/*.json — schema rdf-fitness/1: só agregados numéricos;
   chaves proibidas (task, content, project...) reprovam — é o guard
   anti-vazamento do canal de fitness.

Exit code 0 = tudo válido; 1 = qualquer violação (falha o CI).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
POOL_DIR = ROOT / "agents" / "pool"
FITNESS_DIR = ROOT / "community" / "fitness"

POOL_REQUIRED = {"nome", "tier", "specialty", "model", "ruleset_version",
                 "evolution", "success_rate", "tasks_completed", "tasks_failed", "pontos"}
FITNESS_FORBIDDEN_KEYS = {"task", "tasks", "content", "prompt", "response", "project",
                          "projects", "file", "files", "path", "briefing", "logs"}
FITNESS_BUCKET_NUMERIC = {"tasks_ok", "tasks_fail", "infra_failures", "duel_runs", "duel_ok",
                          "prompt_tokens", "completion_tokens", "cost_usd"}

errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)
    print(f"  [ERRO] {msg}")


def check_pool() -> None:
    print(f"== agents/pool ==")
    files = sorted(POOL_DIR.glob("*.json")) if POOL_DIR.exists() else []
    if not files:
        err("agents/pool/ vazio ou ausente — o pool global é obrigatório")
        return
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            err(f"{f.name}: JSON inválido ({e})")
            continue
        missing = POOL_REQUIRED - set(d)
        if missing:
            err(f"{f.name}: campos ausentes: {sorted(missing)}")
        if not isinstance(d.get("tier"), int) or not 1 <= d.get("tier", 0) <= 4:
            err(f"{f.name}: tier inválido: {d.get('tier')!r}")
        if d.get("tasks_completed") != 0 or d.get("tasks_failed") != 0:
            err(f"{f.name}: pool deve ter stats NEUTRAS (tasks_completed/failed = 0) — "
                f"fenótipo local não entra no git")
        if d.get("pontos") != {"externos": 0, "internos": 0}:
            err(f"{f.name}: pontos devem ser zerados no pool")
        if "/" not in str(d.get("model", "")):
            err(f"{f.name}: model sem prefixo 'provider/': {d.get('model')!r}")
    print(f"  {len(files)} definição(ões) verificada(s)")


def check_fitness() -> None:
    print(f"== community/fitness ==")
    files = [f for f in (sorted(FITNESS_DIR.glob("*.json")) if FITNESS_DIR.exists() else [])]
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            err(f"{f.name}: JSON inválido ({e})")
            continue
        if d.get("schema") != "rdf-fitness/1":
            err(f"{f.name}: schema deve ser 'rdf-fitness/1'")
            continue
        for section in ("models", "rulesets"):
            for key, bucket in d.get(section, {}).items():
                if not isinstance(bucket, dict):
                    err(f"{f.name}: {section}.{key} não é objeto")
                    continue
                leaked = set(bucket) & FITNESS_FORBIDDEN_KEYS
                if leaked:
                    err(f"{f.name}: {section}.{key} contém chaves proibidas: {sorted(leaked)}")
                for k, v in bucket.items():
                    if k in FITNESS_BUCKET_NUMERIC and not isinstance(v, (int, float)):
                        err(f"{f.name}: {section}.{key}.{k} deveria ser numérico")
    print(f"  {len(files)} export(s) de fitness verificado(s)")


if __name__ == "__main__":
    check_pool()
    check_fitness()
    if errors:
        print(f"\n{len(errors)} violação(ões) encontrada(s).")
        sys.exit(1)
    print("\nTodos os schemas válidos.")
