#!/usr/bin/env python3
"""
.claude/hooks/pre_edit_guard.py — Guard de Delegação de Edições

Intercepta Edit e Write, encontra o agente dono do arquivo,
calcula o nível de problema e decide:

  MINOR  (≤ 20 linhas)   → BLOQUEIA → brief para o agente responsável
  MEDIUM (21-100 linhas) → BLOQUEIA → brief + sugestão de escalação
  MAJOR  (>100 linhas ou arquivo arquitetural) → PERMITE Claude,
                            registra override em file_registry + pending_docs

Bypass de emergência: crie o arquivo C:\\RubberDuckFactory\\.edit_override
com o motivo da emergência. O arquivo é consumido (deletado) após um único uso
e o override fica auditado em hooks_audit.log.

Arquivos isentos: .claude/**, agents/active/**, project_ledger/**, etc.
(configurável em agents/file_ownership.json → "exempt")
"""

import fnmatch
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Força UTF-8 no stdout/stderr para evitar UnicodeEncodeError no Windows (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─── Caminhos ────────────────────────────────────────────────────────────────
ROOT           = Path(__file__).resolve().parent.parent.parent
OWNERSHIP_FILE = ROOT / "agents" / "file_ownership.json"
FILE_REGISTRY  = ROOT / "project_ledger" / "file_registry.json"
PENDING_DOCS   = ROOT / "project_ledger" / "pending_docs.json"
AUDIT_LOG      = ROOT / "project_ledger" / "hooks_audit.log"
AGENTS_DIR     = ROOT / "agents" / "active"
OVERRIDE_FLAG  = ROOT / ".edit_override"

# ─── Limiares ────────────────────────────────────────────────────────────────
MINOR_MAX  = 20    # ≤ 20 linhas → MINOR
MEDIUM_MAX = 100   # ≤ 100 linhas → MEDIUM; acima → MAJOR

# Padrões que tornam o arquivo MAJOR independente do tamanho
ARCHITECTURAL = [
    "docker-compose*.yaml", "docker-compose*.yml",
    "Dockerfile*",
    "architecture-map/**",
    ".governance/**",
    "quality_gate_server.py",
    "sovereign_proxy.py",
]

# Padrões built-in isentos (complementam os do JSON)
BUILTIN_EXEMPT = [
    ".claude/**", "agents/active/**", "agents/blacklist/**",
    "agents/file_ownership.json", "agents/clearance_memory/**",
    "project_ledger/**", "memory/**", "qdrant_storage/**",
    ".env", ".env.*", "pyproject.toml", "package.json",
    "tsconfig.json", "uv.lock", "*.lock", "metadata.json", "assets/**",
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rel(file_path: str) -> str:
    """Caminho relativo ao ROOT com barras normais."""
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


def _load_ownership() -> dict:
    try:
        return json.loads(OWNERSHIP_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"patterns": [], "exempt": []}


def _find_owner(rel: str, ownership: dict) -> dict | None:
    for entry in ownership.get("patterns", []):
        if fnmatch.fnmatch(rel, entry["glob"]):
            return entry
    return None


def _load_agent(name: str) -> dict:
    for p in AGENTS_DIR.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("nome", "").lower() == name.lower():
                return d
        except Exception:
            pass
    return {}


def _lines(old: str, new: str) -> int:
    return max(len(old.splitlines()), len(new.splitlines()))


def _classify(lines: int, rel: str) -> str:
    if _matches(rel, ARCHITECTURAL):
        return "MAJOR"
    if lines > MEDIUM_MAX:
        return "MAJOR"
    if lines > MINOR_MAX:
        return "MEDIUM"
    return "MINOR"


def _load_registry() -> dict:
    try:
        d = json.loads(FILE_REGISTRY.read_text(encoding="utf-8"))
        return d.get("files", {})
    except Exception:
        return {}


def _save_registry(files: dict) -> None:
    try:
        current = {}
        if FILE_REGISTRY.exists():
            current = json.loads(FILE_REGISTRY.read_text(encoding="utf-8"))
        current["files"] = files
        FILE_REGISTRY.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _conflict_warning(rel: str, owner: str) -> str | None:
    reg = _load_registry()
    entry = reg.get(rel)
    if not entry:
        return None
    last = entry.get("last_edited_by", owner)
    if last not in (owner, "ARQUITETO"):
        return (
            f"⚠️  CONFLITO: '{rel}' foi editado por '{last}' "
            f"mas o dono é '{owner}'. Verifique sobreposição de responsabilidades."
        )
    return None


def _register_override(rel: str, edited_by: str, level: str, lines: int) -> None:
    """Registra edição MAJOR/override no file_registry e pending_docs."""
    files = _load_registry()
    entry = files.get(rel, {
        "owner": edited_by,
        "created_by": edited_by,
        "created_ts": _ts(),
        "edit_count": 0,
        "co_authors": [],
    })
    entry["last_edited_by"] = edited_by
    entry["last_edit_ts"]   = _ts()
    entry["edit_count"]     = entry.get("edit_count", 0) + 1
    co = entry.setdefault("co_authors", [])
    if edited_by not in co:
        co.append(edited_by)
    files[rel] = entry
    _save_registry(files)
    _add_pending(rel, edited_by, level, lines)


def _add_pending(rel: str, edited_by: str, level: str, lines: int) -> None:
    try:
        if PENDING_DOCS.exists():
            data = json.loads(PENDING_DOCS.read_text(encoding="utf-8"))
        else:
            data = {"pending": []}
        data["pending"].append({
            "file": rel, "edited_by": edited_by,
            "level": level, "lines": lines,
            "ts": _ts(), "status": "PENDING",
        })
        PENDING_DOCS.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _audit(msg: str) -> None:
    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(f"{_ts()} | pre_edit_guard | {msg}\n")
    except Exception:
        pass


def _runner_cmd(agent: str, rel: str, lines: int) -> str:
    task = f"Revise e ajuste o arquivo {rel} ({lines} linhas impactadas). Siga os padrões do projeto."
    return (
        f"uv run python agents/agent_runner.py "
        f"--agent {agent.lower()} "
        f'--task "{task}" '
        f"--files {rel} "
        f"--project RubberDuckFactory"
    )


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception as e:
        print(f"[pre_edit_guard] ERRO ao ler stdin: {e}", file=sys.stderr)
        sys.exit(0)  # fail-open: não bloquear por erro interno

    tool_name  = data.get("tool_name", "")
    inp        = data.get("tool_input", {})
    file_path  = inp.get("file_path", "")
    old_string = inp.get("old_string", "")
    new_string = inp.get("new_string", "") or inp.get("content", "")

    if not file_path:
        sys.exit(0)

    rel = _rel(file_path)

    # ── Bypass de emergência ──────────────────────────────────────────────────
    if OVERRIDE_FLAG.exists():
        try:
            motivo = OVERRIDE_FLAG.read_text(encoding="utf-8").strip() or "sem motivo registrado"
            OVERRIDE_FLAG.unlink()  # consumir o override
        except Exception:
            motivo = "erro ao ler motivo"
        _audit(f"EMERGENCY OVERRIDE | {rel} | motivo: {motivo}")
        _register_override(rel, "ARQUITETO_OVERRIDE", "EMERGENCY", _lines(old_string, new_string))
        print(
            f"[pre_edit_guard] 🚨 EMERGENCY OVERRIDE consumido — {rel}\n"
            f"  Motivo: {motivo}\n"
            f"  Registrado em hooks_audit.log e file_registry.",
            file=sys.stderr,
        )
        sys.exit(0)

    # ── Isenções ──────────────────────────────────────────────────────────────
    ownership   = _load_ownership()
    all_exempt  = BUILTIN_EXEMPT + ownership.get("exempt", [])
    if _matches(rel, all_exempt):
        sys.exit(0)

    # ── Encontra dono ─────────────────────────────────────────────────────────
    owner_entry = _find_owner(rel, ownership)
    if not owner_entry:
        # Arquivo sem dono → passa, mas registra como UNOWNED
        _add_pending(rel, "ARQUITETO", "UNOWNED", _lines(old_string, new_string))
        _audit(f"UNOWNED | {rel}")
        sys.exit(0)

    owner_name = owner_entry["agent"]
    owner_tier = owner_entry.get("tier", 1)

    # ── Nível do problema ─────────────────────────────────────────────────────
    lines = _lines(old_string, new_string)
    level = _classify(lines, rel)

    # ── Conflito de autoria ───────────────────────────────────────────────────
    conflict = _conflict_warning(rel, owner_name)

    # ── Estado do agente ──────────────────────────────────────────────────────
    agent_data      = _load_agent(owner_name)
    evolution       = agent_data.get("evolution", "Stable")
    is_degraded     = evolution == "Degraded"

    # ── MAJOR → Claude assume com auditoria ──────────────────────────────────
    if level == "MAJOR":
        _register_override(rel, "ARQUITETO", "MAJOR", lines)
        _audit(f"MAJOR_OVERRIDE | {rel} | {lines} linhas | owner={owner_name}")
        parts = [
            f"[pre_edit_guard] ✅ MAJOR — Arquiteto assume: {rel}",
            f"  Linhas: {lines} | Dono original: {owner_name} (Tier {owner_tier})",
            f"  Registrado em file_registry.json + pending_docs.json (Quill notificado).",
        ]
        if conflict:
            parts.append(f"  {conflict}")
        print("\n".join(parts), file=sys.stderr)
        sys.exit(0)

    # ── Agente Degraded + não-MAJOR → escala para Arquiteto ──────────────────
    if is_degraded:
        _register_override(rel, "ARQUITETO", f"{level}_DEGRADED_ESCALATION", lines)
        _audit(f"DEGRADED_ESCALATION | {rel} | agent={owner_name}")
        print(
            f"[pre_edit_guard] ⚠️  {owner_name} está Degraded — Arquiteto assume {rel} com auditoria.",
            file=sys.stderr,
        )
        sys.exit(0)

    # ── MINOR / MEDIUM → BLOQUEAR ─────────────────────────────────────────────
    _add_pending(rel, owner_name, level, lines)
    _audit(f"BLOCKED_{level} | {rel} | {lines} linhas | owner={owner_name}")

    icon  = "🟡" if level == "MINOR" else "🟠"
    label = f"{icon} {level}"

    escalation = ""
    if level == "MEDIUM":
        senior = "Shadow" if owner_tier < 3 else owner_name
        escalation = (
            f"\n  Se houver impacto arquitetural, escale para {senior} "
            f"com --agent {senior.lower()} no comando abaixo."
        )

    cmd = _runner_cmd(owner_name, rel, lines)

    # stdout → contexto para Claude (exit 2)
    msg = "\n".join(filter(None, [
        f"[pre_edit_guard] EDIÇÃO BLOQUEADA — {label}",
        f"  Arquivo     : {rel}",
        f"  Responsável : {owner_name}  (Tier {owner_tier} | {evolution})",
        f"  Linhas      : {lines}",
        escalation,
        f"",
        f"  Formule o briefing e delegue via:",
        f"  {cmd}",
        f"",
        f"  Regra: edições em arquivos mapeados devem passar pelo agente dono.",
        f"  Para override de emergência: crie o arquivo .edit_override com o motivo.",
        conflict,
    ]))

    print(msg)  # stdout → Claude recebe como contexto
    print(f"[pre_edit_guard] ⛔ {level} | {rel} → {owner_name}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
