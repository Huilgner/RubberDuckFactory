#!/usr/bin/env python3
"""
agents/sync_pool.py -- Sincronizador Pool Global <-> Squad Local

Modelo de propagacao do RDF ("genoma no git, fenotipo local"):

  agents/pool/    VERSIONADO no git. Definicoes dos agentes (nome, tier, modelo,
                  especialidade, ruleset) com stats neutras. E o que todos os
                  usuarios do RDF compartilham -- o "genoma" do squad.

  agents/active/  IGNORADO pelo git. Copia viva local: acumula pontos,
                  success_rate e evolution de CADA usuario, offline,
                  sem nunca sair da maquina -- o "fenotipo".

Comandos:
  python agents/sync_pool.py                      # status: diff pool vs active
  python agents/sync_pool.py --bootstrap          # cria active/ a partir do pool (so os ausentes)
  python agents/sync_pool.py --update             # puxa definicoes novas do pool preservando stats locais
  python agents/sync_pool.py --promote NOME       # publica definicao local no pool (sanitizada, p/ PR)
  python agents/sync_pool.py --seed-pool          # gera o pool a partir do active atual (setup inicial)
"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import json
from pathlib import Path

ROOT_DIR   = Path(__file__).parent.parent
ACTIVE_DIR = ROOT_DIR / "agents" / "active"
POOL_DIR   = ROOT_DIR / "agents" / "pool"

# Campos de DEFINICAO (genoma): viajam pelo git
DEFINITION_FIELDS = ["nome", "tier", "specialty", "model", "ruleset_version", "status", "system_prompt"]

# Campos de ESTADO (fenotipo): nunca saem da maquina; seeds neutros no pool
STATE_SEED = {
    "evolution":       "Stable",
    "success_rate":    100.0,
    "tasks_completed": 0,
    "tasks_failed":    0,
    "pontos":          {"externos": 0, "internos": 0},
}


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def sanitize(agent: dict) -> dict:
    """Extrai a definicao compartilhavel: campos de genoma + stats neutras."""
    out = {k: agent[k] for k in DEFINITION_FIELDS if k in agent}
    out.update(json.loads(json.dumps(STATE_SEED)))  # copia profunda dos seeds
    return out


def seed_pool(force: bool = False) -> None:
    """Gera agents/pool/ a partir do active atual (setup inicial do repositorio)."""
    created = 0
    for src in sorted(ACTIVE_DIR.glob("*.json")):
        dst = POOL_DIR / src.name
        if dst.exists() and not force:
            print(f"  [SKIP] {dst.name} ja existe no pool (use --force para sobrescrever)")
            continue
        _write(dst, sanitize(_read(src)))
        created += 1
        print(f"  [POOL] {src.name} -> definicao sanitizada publicada")
    print(f"\n{created} definicao(oes) gravada(s) em agents/pool/")


def bootstrap() -> None:
    """Cria os agentes locais ausentes a partir do pool (nao toca nos existentes)."""
    if not POOL_DIR.exists():
        raise SystemExit("agents/pool/ nao existe. Rode --seed-pool na maquina de origem.")
    created = 0
    for src in sorted(POOL_DIR.glob("*.json")):
        dst = ACTIVE_DIR / src.name
        if dst.exists():
            continue
        _write(dst, _read(src))
        created += 1
        print(f"  [BOOTSTRAP] {src.name} -> squad local")
    print(f"\n{created} agente(s) inicializado(s) em agents/active/ "
          f"({len(list(ACTIVE_DIR.glob('*.json')))} no total)")


def update() -> None:
    """Puxa mudancas de DEFINICAO do pool para o active, preservando stats locais."""
    if not POOL_DIR.exists():
        raise SystemExit("agents/pool/ nao existe.")
    changed = 0
    for src in sorted(POOL_DIR.glob("*.json")):
        dst = ACTIVE_DIR / src.name
        pool_def = _read(src)
        if not dst.exists():
            _write(dst, pool_def)
            print(f"  [NOVO] {src.name} (agente novo vindo do pool)")
            changed += 1
            continue
        local = _read(dst)
        diffs = []
        for k in DEFINITION_FIELDS:
            if k in pool_def and local.get(k) != pool_def[k]:
                diffs.append(f"{k}: {local.get(k)!r} -> {pool_def[k]!r}")
                local[k] = pool_def[k]
        if diffs:
            _write(dst, local)
            changed += 1
            print(f"  [UPDATE] {src.name}: " + "; ".join(diffs))
    print(f"\n{changed} agente(s) atualizado(s). Stats locais preservados.")


def promote(name: str) -> None:
    """Publica a definicao de um agente local no pool (sanitizada, sem stats)."""
    src = ACTIVE_DIR / f"{name.lower()}.json"
    if not src.exists():
        raise SystemExit(f"Agente '{name}' nao encontrado em agents/active/")
    _write(POOL_DIR / src.name, sanitize(_read(src)))
    print(f"[PROMOTE] {src.name} -> agents/pool/ (stats zeradas)")
    print("Revise e abra um PR para compartilhar com o squad global.")


def status() -> None:
    """Mostra o diff entre pool e active."""
    pool   = {p.name: _read(p) for p in POOL_DIR.glob("*.json")} if POOL_DIR.exists() else {}
    active = {p.name: _read(p) for p in ACTIVE_DIR.glob("*.json")} if ACTIVE_DIR.exists() else {}

    print(f"Pool (git): {len(pool)} agentes | Active (local): {len(active)} agentes\n")
    for name in sorted(set(pool) | set(active)):
        if name not in active:
            print(f"  [SO NO POOL]   {name}  -> rode --bootstrap ou --update")
        elif name not in pool:
            print(f"  [SO LOCAL]     {name}  -> rode --promote {name.replace('.json','')} para publicar")
        else:
            diffs = [k for k in DEFINITION_FIELDS
                     if pool[name].get(k) != active[name].get(k) and k in pool[name]]
            if diffs:
                print(f"  [DIVERGENTE]   {name}  campos: {', '.join(diffs)}  -> --update puxa do pool")
            else:
                a = active[name]
                print(f"  [OK]           {name}  (sr={a.get('success_rate')}% | {a.get('evolution')})")


def main() -> None:
    p = argparse.ArgumentParser(description="Sincronizador Pool Global <-> Squad Local (RDF)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--bootstrap", action="store_true", help="cria agentes locais ausentes a partir do pool")
    g.add_argument("--update",    action="store_true", help="puxa definicoes do pool preservando stats locais")
    g.add_argument("--promote",   metavar="NOME",      help="publica definicao local no pool (sanitizada)")
    g.add_argument("--seed-pool", action="store_true", help="gera o pool a partir do active atual")
    p.add_argument("--force", action="store_true", help="com --seed-pool: sobrescreve definicoes existentes")
    args = p.parse_args()

    if args.seed_pool:
        seed_pool(force=args.force)
    elif args.bootstrap:
        bootstrap()
    elif args.update:
        update()
    elif args.promote:
        promote(args.promote)
    else:
        status()


if __name__ == "__main__":
    main()
