import json
import sys
from pathlib import Path

FREEZE_FLAG = Path(r"C:\RubberDuckFactory\.code_freeze")

if not FREEZE_FLAG.exists():
    sys.exit(0)

since = FREEZE_FLAG.read_text(encoding="utf-8").strip()[:19]
data = json.load(sys.stdin)
tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})

if tool_name in ("Edit", "Write"):
    print(f"[HOOK FREEZE] Code Freeze ativo desde {since} — edições bloqueadas durante quality gate.")
    sys.exit(2)

if tool_name == "Bash":
    command = tool_input.get("command", "")
    BLOCKED_GIT = ["git commit", "git push", "git merge", "git rebase"]
    if any(op in command for op in BLOCKED_GIT):
        print(f"[HOOK FREEZE] Code Freeze ativo desde {since} — operações git de escrita bloqueadas.")
        sys.exit(2)

sys.exit(0)
