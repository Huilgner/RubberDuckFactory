import json
import sys
import os
from datetime import datetime

data = json.load(sys.stdin)
tool_name = data.get("tool_name", "unknown")
tool_input = data.get("tool_input", {})

if tool_name == "Bash":
    summary = tool_input.get("command", "")[:150]
elif tool_name in ("Edit", "Write"):
    summary = tool_input.get("file_path", "")
else:
    summary = str(tool_input)[:100]

log_path = r"C:\RubberDuckFactory\project_ledger\hooks_audit.log"
os.makedirs(os.path.dirname(log_path), exist_ok=True)

with open(log_path, "a", encoding="utf-8") as f:
    f.write(f"{datetime.now().isoformat()} | {tool_name} | {summary}\n")

sys.exit(0)
