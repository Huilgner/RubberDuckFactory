import json
import re
import sys

data = json.load(sys.stdin)
command = data.get("tool_input", {}).get("command", "")

BLOCKED = [
    (r"rm\s+-[rRf]*f[rR]?\s+", "rm -rf"),
    (r"Remove-Item.*-Recurse.*-Force.*(?:agents|\.governance|project_ledger)", "Remove-Item em path protegido"),
    (r"git\s+reset\s+--hard", "git reset --hard"),
    (r"git\s+push\s+.*(-f\b|--force)", "git push --force"),
    (r"git\s+branch\s+-[Dd]\s+main\b", "delete branch main"),
    (r"DROP\s+(TABLE|DATABASE)\s", "DROP TABLE/DATABASE"),
    (r"format\s+[a-zA-Z]:", "format de disco"),
]

CAUTION_MODELS = [
    (r"gemini-1[._-]5", "gemini-1.5 descontinuado — use gemini-2.5"),
    (r"['\"][\w/.-]+-thinking['\"]", "modelo -thinking (>10% alucinacao em tarefas simples)"),
    (r"['\"][\w/.-]+-r1['\"]", "modelo -r1 (categoria reasoning com falhas conhecidas)"),
    (r"['\"](?![\w\-]+/)(llama|gemma|mistral)\b", "modelo sem prefixo provider/ — use formato provider/modelo"),
]

for pattern, label in BLOCKED:
    if re.search(pattern, command, re.IGNORECASE):
        print(f"[HOOK PRE_BASH] Bloqueado: '{label}' detectado no comando.")
        sys.exit(2)

for pattern, label in CAUTION_MODELS:
    if re.search(pattern, command, re.IGNORECASE):
        print(f"[HOOK CAUTION] Aviso: {label}")

sys.exit(0)
