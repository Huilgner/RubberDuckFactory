import json
import sys

data = json.load(sys.stdin)
file_path = data.get("tool_input", {}).get("file_path", "").replace("\\", "/")

PROTECTED = [
    (".governance/hr_policies.md", "edições requerem quórum Tier 3 (Shadow)"),
    ("agents/blacklist/", "blacklist requer Shadow + quórum aprovado"),
]

for protected_path, reason in PROTECTED:
    if protected_path in file_path:
        print(f"[HOOK GOVERNANCE] Bloqueado: '{file_path}' — {reason}")
        sys.exit(2)

sys.exit(0)
