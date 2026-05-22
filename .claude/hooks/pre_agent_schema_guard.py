import json
import os
import sys

data = json.load(sys.stdin)
tool_name = data.get("tool_name", "")
tool_input = data.get("tool_input", {})
file_path_raw = tool_input.get("file_path", "")
file_path = file_path_raw.replace("\\", "/")

if "agents/active/" not in file_path or not file_path.endswith(".json"):
    sys.exit(0)

if tool_name == "Write":
    content = tool_input.get("content", "")
elif tool_name == "Edit":
    try:
        with open(file_path_raw, "r", encoding="utf-8") as f:
            content = f.read()
        old_str = tool_input.get("old_string", "")
        new_str = tool_input.get("new_string", "")
        replace_all = tool_input.get("replace_all", False)
        content = content.replace(old_str, new_str) if replace_all else content.replace(old_str, new_str, 1)
    except Exception as e:
        print(f"[HOOK SCHEMA] Não foi possível simular edição: {e}")
        sys.exit(0)
else:
    sys.exit(0)

try:
    agent = json.loads(content)
except json.JSONDecodeError as e:
    print(f"[HOOK SCHEMA] JSON inválido após edição: {e}")
    sys.exit(2)

REQUIRED = ["nome", "tier", "evolution", "model", "pontos"]
missing = [f for f in REQUIRED if f not in agent]
if missing:
    print(f"[HOOK SCHEMA] Campos obrigatórios ausentes: {missing}")
    sys.exit(2)

if agent["evolution"] not in {"Stable", "Mutating", "Degraded"}:
    print(f"[HOOK SCHEMA] evolution inválido: '{agent['evolution']}' — use Stable, Mutating ou Degraded")
    sys.exit(2)

if not isinstance(agent["tier"], int) or agent["tier"] not in [1, 2, 3, 4]:
    print(f"[HOOK SCHEMA] tier inválido: '{agent['tier']}' — deve ser 1, 2, 3 ou 4")
    sys.exit(2)

pontos = agent.get("pontos", {})
ext = pontos.get("externos")
int_ = pontos.get("internos")
if not isinstance(ext, (int, float)) or not isinstance(int_, (int, float)):
    print("[HOOK SCHEMA] pontos deve conter 'externos' e 'internos' numéricos")
    sys.exit(2)
if ext < 0 or int_ < 0:
    print("[HOOK SCHEMA] pontos não podem ser negativos")
    sys.exit(2)

sys.exit(0)
