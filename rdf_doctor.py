#!/usr/bin/env python3
"""
rdf_doctor.py — Diagnóstico de instalação do RubberDuckFactory.

Para quem acabou de clonar o repositório:

    python rdf_doctor.py           # diagnostico completo
    python rdf_doctor.py --fix     # tambem executa o bootstrap do squad

Verifica: versão do Python, dependências, .env/API key, squad local
(bootstrap a partir do pool), ledger gravável, orçamento e serviços Docker.
"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import importlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agents"))

OK, WARN, FAIL = "✅", "⚠️ ", "❌"
failures = 0
warnings = 0


def report(status: str, label: str, detail: str = "") -> None:
    global failures, warnings
    if status == FAIL:
        failures += 1
    elif status == WARN:
        warnings += 1
    print(f"  {status} {label}" + (f" — {detail}" if detail else ""))


def check_python() -> None:
    v = sys.version_info
    if (v.major, v.minor) >= (3, 12):
        report(OK, f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        report(FAIL, f"Python {v.major}.{v.minor}", "requer >= 3.12 (pyproject.toml)")


def check_deps() -> None:
    required = ["httpx", "dotenv"]
    optional = {"mcp": "quality gate MCP", "pytest": "suite de testes",
                "yaml": "validacao de infra", "chromadb": "cache semantico"}
    for mod in required:
        try:
            importlib.import_module(mod)
            report(OK, f"dependencia: {mod}")
        except ImportError:
            report(FAIL, f"dependencia: {mod}", "pip install httpx python-dotenv (ou: uv sync)")
    for mod, why in optional.items():
        try:
            importlib.import_module(mod)
            report(OK, f"opcional: {mod}")
        except ImportError:
            report(WARN, f"opcional: {mod}", f"ausente — {why} indisponivel")


def check_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        report(FAIL, ".env", "copie .env.example para .env e preencha OPENROUTER_API_KEY")
        return
    from dotenv import load_dotenv
    load_dotenv(env)
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if key.startswith("sk-or-"):
        report(OK, "OPENROUTER_API_KEY presente")
    elif key:
        report(WARN, "OPENROUTER_API_KEY", "presente mas nao parece uma chave OpenRouter (sk-or-...)")
    else:
        report(FAIL, "OPENROUTER_API_KEY", "vazia no .env — agentes remotos nao funcionarao")


def check_squad(fix: bool) -> None:
    active = ROOT / "agents" / "active"
    pool = ROOT / "agents" / "pool"
    n_active = len(list(active.glob("*.json"))) if active.exists() else 0
    n_pool = len(list(pool.glob("*.json"))) if pool.exists() else 0
    if n_active:
        report(OK, f"squad local: {n_active} agente(s) em agents/active/")
    elif n_pool and fix:
        import sync_pool
        sync_pool.bootstrap()
        report(OK, f"squad local inicializado a partir do pool ({n_pool} agentes)")
    elif n_pool:
        report(WARN, "squad local vazio",
               f"pool tem {n_pool} agentes — rode: python agents/sync_pool.py --bootstrap "
               "(ou use --fix aqui; o runner tambem inicializa sozinho no primeiro uso)")
    else:
        report(FAIL, "squad", "nem agents/active/ nem agents/pool/ tem agentes")


def check_ledger() -> None:
    try:
        import ledger_io
        with ledger_io.history_lock():
            pass
        report(OK, "ledger gravavel (lock adquirido e liberado)")
        n = len(ledger_io.read_history())
        report(OK, f"historico: {n} evento(s)")
    except Exception as e:
        report(FAIL, "ledger", str(e))


def check_budget() -> None:
    budget = ROOT / ".governance" / "budget.json"
    if not budget.exists():
        report(WARN, "orcamento", ".governance/budget.json ausente — chamadas SEM teto de gasto")
        return
    try:
        b = json.loads(budget.read_text(encoding="utf-8"))
        enforce = "bloqueia" if b.get("enforce", True) else "so avisa"
        report(OK, f"orcamento: ${b.get('daily_usd', '?')}/dia, ${b.get('monthly_usd', '?')}/mes ({enforce})")
    except Exception as e:
        report(FAIL, "orcamento", f"budget.json invalido: {e}")


def check_docker() -> None:
    try:
        import httpx
    except ImportError:
        return
    services = {
        "board (dashboard)": "http://localhost:3001",
        "qdrant (memoria vetorial)": "http://localhost:6333/healthz",
        "mcp-server (remember/recall)": "http://localhost:8001/mcp",
    }
    for name, url in services.items():
        try:
            r = httpx.get(url, timeout=3.0)
            if r.status_code < 500:
                report(OK, name)
            else:
                report(WARN, name, f"HTTP {r.status_code}")
        except Exception:
            report(WARN, name, "inacessivel — rode: docker compose up -d (opcional para o runner)")


def main() -> None:
    p = argparse.ArgumentParser(description="Diagnostico de instalacao do RubberDuckFactory")
    p.add_argument("--fix", action="store_true", help="executa o bootstrap do squad se necessario")
    args = p.parse_args()

    print("=" * 60)
    print("  RDF DOCTOR — diagnostico da instalacao")
    print("=" * 60)
    print("\n[Python e dependencias]")
    check_python()
    check_deps()
    print("\n[Configuracao]")
    check_env()
    check_budget()
    print("\n[Squad e ledger]")
    check_squad(args.fix)
    check_ledger()
    print("\n[Servicos Docker (opcionais para o runner)]")
    check_docker()

    print("\n" + "=" * 60)
    if failures:
        print(f"  {failures} problema(s) bloqueante(s), {warnings} aviso(s). Corrija os ❌ acima.")
        sys.exit(1)
    print(f"  Instalacao OK ({warnings} aviso(s)). Teste com:")
    print("  python agents/agent_runner.py --agent heuristic --task 'LOCAL_RUN: git status'")


if __name__ == "__main__":
    main()
