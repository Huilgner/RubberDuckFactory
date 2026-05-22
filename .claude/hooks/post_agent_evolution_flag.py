import json
import sys

data = json.load(sys.stdin)
tool_input = data.get("tool_input", {})
file_path_raw = tool_input.get("file_path", "")
file_path = file_path_raw.replace("\\", "/")

if "agents/active/" not in file_path or not file_path.endswith(".json"):
    sys.exit(0)

try:
    with open(file_path_raw, "r", encoding="utf-8") as f:
        agent = json.load(f)
except Exception:
    sys.exit(0)

nome = agent.get("nome", "?")
tier = agent.get("tier", 1)
evolution = agent.get("evolution", "Stable")
success_rate = agent.get("success_rate", 100)
pontos = agent.get("pontos", {})
ext = pontos.get("externos", 0)
int_ = pontos.get("internos", 0)

warnings = []

if success_rate < 70 and evolution != "Degraded":
    warnings.append(f"success_rate={success_rate}% < 70% — considere evolution: Degraded")
elif success_rate < 85 and evolution == "Stable":
    warnings.append(f"success_rate={success_rate}% < 85% — considere evolution: Mutating")

THRESHOLDS = {2: (50, 20), 3: (150, 60), 4: (400, 150)}
if tier in THRESHOLDS:
    min_ext, min_int = THRESHOLDS[tier]
    if ext < min_ext or int_ < min_int:
        warnings.append(
            f"Tier {tier} requer {min_ext}ext/{min_int}int — atual: {ext}ext/{int_}int"
        )

if warnings:
    print(f"[HOOK EVOLUCAO] {nome}:")
    for w in warnings:
        print(f"  ! {w}")

sys.exit(0)
