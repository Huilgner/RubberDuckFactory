#!/usr/bin/env python3
"""
.claude/hooks/post_file_registry.py — Atualização do File Registry pós-edição

Roda após cada Edit/Write bem-sucedido.
Registra em project_ledger/file_registry.json:
  - last_edited_by: "ARQUITETO" (Claude sempre aplica o Edit diretamente)
  - last_edit_ts, edit_count, co_authors

Para marcar uma edição como sendo DE um agente (não do Arquiteto),
use: uv run python agents/agent_runner.py --agent <nome> --files <caminho>
O agent_runner atualizará o registry com o nome correto do agente.

Arquivos isentos (mesmo lista do pre_edit_guard) não são registrados.
"""

import fnmatch
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT          = Path(__file__).resolve().parent.parent.parent
FILE_REGISTRY = ROOT / "project_ledger" / "file_registry.json"
OWNERSHIP_FILE = ROOT / "agents" / "file_ownership.json"

BUILTIN_EXEMPT = [
    ".claude/**", "agents/active/**", "agents/blacklist/**",
    "agents/file_ownership.json", "agents/clearance_memory/**",
    "project_ledger/**", "memory/**", "qdrant_storage/**",
    ".env", ".env.*", "pyproject.toml", "package.json",
    "tsconfig.json", "uv.lock", "*.lock", "metadata.json", "assets/**",
]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rel(file_path: str) -> str:
    try:
        return str(Path(file_path).resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return Path(file_path).name


def _matches(rel: str, patterns: list[str]) -> bool:
    p = rel.replace("\\", "/")
    name = Path(p).name
    for pat in patterns:
        pat = pat.replace("\\", "/")
        if fnmatch.fnmatch(p, pat) or fnmatch.fnmatch(name, pat):
            return True
    return False


def _load_ownership_exempt() -> list[str]:
    try:
        d = json.loads(OWNERSHIP_FILE.read_text(encoding="utf-8"))
        return d.get("exempt", [])
    except Exception:
        return []


def _load_registry() -> dict:
    try:
        d = json.loads(FILE_REGISTRY.read_text(encoding="utf-8"))
        return d
    except Exception:
        return {"_schema": "1.0", "files": {}}


def _save_registry(data: dict) -> None:
    try:
        FILE_REGISTRY.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _find_owner(rel: str) -> str | None:
    try:
        d = json.loads(OWNERSHIP_FILE.read_text(encoding="utf-8"))
        for entry in d.get("patterns", []):
            if fnmatch.fnmatch(rel, entry["glob"]):
                return entry["agent"]
    except Exception:
        pass
    return None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    inp       = data.get("tool_input", {})
    file_path = inp.get("file_path", "")
    if not file_path:
        sys.exit(0)

    rel = _rel(file_path)

    # Isenções
    all_exempt = BUILTIN_EXEMPT + _load_ownership_exempt()
    if _matches(rel, all_exempt):
        sys.exit(0)

    # Carrega registry
    registry = _load_registry()
    files    = registry.setdefault("files", {})

    owner = _find_owner(rel) or "ARQUITETO"

    entry = files.get(rel, {
        "owner":      owner,
        "created_by": "ARQUITETO",
        "created_ts": _ts(),
        "edit_count": 0,
        "co_authors": [],
    })

    # Só atualiza last_edited_by se a última edição não foi marcada por um agente
    # (o agent_runner.py pode sobrescrever com o nome do agente depois)
    entry["last_edited_by"] = "ARQUITETO"
    entry["last_edit_ts"]   = _ts()
    entry["edit_count"]     = entry.get("edit_count", 0) + 1
    co = entry.setdefault("co_authors", [])
    if "ARQUITETO" not in co:
        co.append("ARQUITETO")

    files[rel] = entry
    _save_registry(registry)
    sys.exit(0)


if __name__ == "__main__":
    main()
