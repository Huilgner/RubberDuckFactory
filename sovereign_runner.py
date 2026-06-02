#!/usr/bin/env python3
"""
sovereign_runner.py — Interface CLI para o Sovereign do Squad RubberDuckFactory

O Sovereign e o Analista de Negocios Tecnico Senior do squad: planeja, estrutura e documenta.
Ele NAO executa codigo — transforma demandas em Briefings Tecnicos e Blueprints de Produto.

Uso:
  uv run python sovereign_runner.py --projeto CastleVote --demanda "Adicionar novo estado"
  uv run python sovereign_runner.py --projeto SIGO_FENIX --blueprint
  uv run python sovereign_runner.py --help

Artefatos gerados em: docs/blueprints/<PROJETO>/blueprint_Rnn.md
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx
from dotenv import load_dotenv

ROOT_DIR       = Path(__file__).parent
AGENTS_DIR     = ROOT_DIR / "agents" / "active"
LEDGER_DIR     = ROOT_DIR / "project_ledger"
BLUEPRINTS_DIR = ROOT_DIR / "docs" / "blueprints"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

load_dotenv(ROOT_DIR / ".env")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

if not OPENROUTER_API_KEY:
    raise SystemExit("OPENROUTER_API_KEY nao encontrada no .env")

SOVEREIGN_MAX_TOKENS = 8000  # Blueprints sao documentos longos


# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------

def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_ledger(entry: dict) -> None:
    ledger = LEDGER_DIR / "agent_ledger.log"
    if ledger.exists():
        with open(ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Carregamento do Sovereign
# ---------------------------------------------------------------------------

def load_sovereign() -> dict:
    for path in AGENTS_DIR.glob("*.json"):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            if d.get("nome", "").lower() == "sovereign":
                d["_file"] = str(path)
                return d
        except Exception:
            continue
    raise SystemExit("Agente 'Sovereign' nao encontrado em agents/active/")


# ---------------------------------------------------------------------------
# Gerenciamento de Blueprints
# ---------------------------------------------------------------------------

def get_latest_blueprint(projeto: str) -> tuple:
    """Retorna (caminho, conteudo) do blueprint mais recente, ou (None, None)."""
    proj_dir = BLUEPRINTS_DIR / projeto
    if not proj_dir.exists():
        return None, None
    blueprints = sorted(proj_dir.glob("blueprint_R*.md"), reverse=True)
    if not blueprints:
        return None, None
    latest = blueprints[0]
    return latest, latest.read_text(encoding="utf-8")


def next_blueprint_path(projeto: str) -> Path:
    """Retorna o caminho para a proxima revisao do blueprint."""
    proj_dir = BLUEPRINTS_DIR / projeto
    proj_dir.mkdir(parents=True, exist_ok=True)
    blueprints = sorted(proj_dir.glob("blueprint_R*.md"), reverse=True)
    if not blueprints:
        return proj_dir / "blueprint_R00.md"
    match = re.search(r"R(\d+)", blueprints[0].name)
    if match:
        return proj_dir / f"blueprint_R{int(match.group(1)) + 1:02d}.md"
    return proj_dir / "blueprint_R00.md"


def list_blueprints(projeto: str) -> None:
    """Lista todas as revisoes do blueprint de um projeto."""
    proj_dir = BLUEPRINTS_DIR / projeto
    if not proj_dir.exists():
        print(f"Nenhum blueprint encontrado para '{projeto}'.")
        return
    blueprints = sorted(proj_dir.glob("blueprint_R*.md"))
    if not blueprints:
        print(f"Nenhum blueprint encontrado para '{projeto}'.")
        return
    print(f"Blueprints de {projeto}:")
    for bp in blueprints:
        size = bp.stat().st_size
        print(f"  {bp.name}  ({size} bytes)")


# ---------------------------------------------------------------------------
# Chamada ao Sovereign via OpenRouter
# ---------------------------------------------------------------------------

def call_sovereign(sovereign: dict, prompt: str) -> dict:
    model  = sovereign.get("model", "anthropic/claude-sonnet-4-5")
    system = sovereign.get("system_prompt", "")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://github.com/Huilgner/RubberDuckFactory",
        "X-Title":       "RubberDuckFactory-Sovereign",
    }
    payload = {
        "model":       model,
        "messages":    [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens":  SOVEREIGN_MAX_TOKENS,
    }

    try:
        with httpx.Client(timeout=240.0) as client:
            resp = client.post(OPENROUTER_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data  = resp.json()
            usage = data.get("usage", {})
            return {
                "content":           (data["choices"][0]["message"]["content"] or "").strip(),
                "prompt_tokens":     usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "success":           True,
                "error":             None,
            }
    except httpx.HTTPStatusError as e:
        return {
            "content": "", "prompt_tokens": 0, "completion_tokens": 0,
            "success": False,
            "error":   f"HTTP {e.response.status_code}: {e.response.text[:300]}",
        }
    except Exception as e:
        return {"content": "", "prompt_tokens": 0, "completion_tokens": 0,
                "success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Modos de execucao
# ---------------------------------------------------------------------------

def run_sovereign(projeto: str, demanda: str) -> None:
    """Processa uma demanda e gera/atualiza o Blueprint do projeto."""
    sovereign = load_sovereign()
    nome  = sovereign.get("nome", "Sovereign")
    model = sovereign.get("model", "?")

    print("=" * 60)
    print(f"  SOVEREIGN — {nome}  |  Tier 4 Architect")
    print(f"  Projeto : {projeto}")
    print(f"  Modelo  : {model}")
    print("=" * 60)
    print()

    # Carrega contexto (blueprint atual)
    bp_path, bp_content = get_latest_blueprint(projeto)
    if bp_path:
        print(f"  Contexto: {bp_path.name} carregado ({bp_path.stat().st_size} bytes)")
        context_block = (
            f"\n\n=== BLUEPRINT ATUAL ({bp_path.name}) ===\n"
            f"{bp_content}\n"
            f"=== FIM DO BLUEPRINT ==="
        )
    else:
        print(f"  Contexto: nenhum blueprint anterior — sera emissao R00")
        context_block = "\n\n[Nenhum blueprint anterior encontrado. Esta sera a emissao inicial R00.]"

    print()
    print(f"DEMANDA:\n{demanda}")
    print()
    print("Processando...")
    print()

    full_prompt = (
        f"sovereign: {demanda}\n\n"
        f"Projeto: {projeto}"
        f"{context_block}"
    )

    resultado = call_sovereign(sovereign, full_prompt)

    if not resultado["success"]:
        print(f"ERRO: {resultado['error']}")
        _append_ledger({
            "ts":      _ts(),
            "type":    "TAREFA_FALHA",
            "agent":   nome,
            "project": projeto,
            "reason":  resultado["error"],
        })
        return

    output = resultado["content"]

    # Salva artefato
    out_path = next_blueprint_path(projeto)
    out_path.write_text(output, encoding="utf-8")

    print(f"Blueprint salvo: {out_path}")
    print(f"Tokens: {resultado['prompt_tokens']} in / {resultado['completion_tokens']} out")
    print()
    print("-" * 60)
    print(output)
    print("-" * 60)

    # Log no ledger
    _append_ledger({
        "ts":      _ts(),
        "type":    "TAREFA_OK",
        "agent":   nome,
        "project": projeto,
        "reason":  f"{out_path.name} gerado | demanda: {demanda[:100]}",
    })


def show_blueprint(projeto: str) -> None:
    """Exibe o blueprint mais recente do projeto."""
    bp_path, bp_content = get_latest_blueprint(projeto)
    if not bp_path:
        print(f"Nenhum blueprint encontrado para '{projeto}'.")
        return
    print(f"=== {bp_path.name} ({bp_path.stat().st_size} bytes) ===")
    print()
    print(bp_content)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sovereign — Analista de Negocios Tecnico Senior do RubberDuckFactory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  uv run python sovereign_runner.py -p CastleVote -d \"Expandir para outros estados\"\n"
            "  uv run python sovereign_runner.py -p SIGO_FENIX --blueprint\n"
            "  uv run python sovereign_runner.py -p SIGO_FENIX --listar\n"
        ),
    )
    parser.add_argument("--projeto", "-p", required=True, metavar="NOME",
                        help="Nome do projeto (ex: CastleVote, SIGO_FENIX)")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demanda", "-d", metavar="TEXTO",
                       help="Demanda em linguagem natural para o Sovereign processar")
    group.add_argument("--blueprint", "-b", action="store_true",
                       help="Exibe o blueprint mais recente do projeto")
    group.add_argument("--listar", "-l", action="store_true",
                       help="Lista todas as revisoes de blueprint do projeto")

    args = parser.parse_args()

    if args.blueprint:
        show_blueprint(args.projeto)
    elif args.listar:
        list_blueprints(args.projeto)
    else:
        run_sovereign(args.projeto, args.demanda)


if __name__ == "__main__":
    main()
