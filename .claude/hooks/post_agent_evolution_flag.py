"""
post_agent_evolution_flag.py — Hook PostToolUse: Edit, Write

Dispara após qualquer edição de JSON em agents/active/.
Ações:
  1. Calcula o estado evolutivo correto baseado em success_rate
  2. Se o estado mudou → aplica a transição diretamente no JSON
  3. Registra toda transição de estado em project_ledger/agent_ledger.log (JSONL)
  4. Avisa sobre pontos abaixo do threshold do tier
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 stdout to avoid cp1252 encoding errors on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def compute_evolution(sr: float) -> str:
    if sr >= 85.0:
        return "Stable"
    elif sr >= 70.0:
        return "Mutating"
    else:
        return "Degraded"


def append_ledger(entry: dict, ledger_path: Path) -> None:
    line = json.dumps(entry, ensure_ascii=False)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ─── Main ─────────────────────────────────────────────────────────────────────

data = json.load(sys.stdin)
tool_input = data.get("tool_input", {})
file_path_raw = tool_input.get("file_path", "")
file_path = file_path_raw.replace("\\", "/")

# Só atua em JSONs de agentes ativos
if "agents/active/" not in file_path or not file_path.endswith(".json"):
    sys.exit(0)

agent_path = Path(file_path_raw)
try:
    agent = json.loads(agent_path.read_text(encoding="utf-8"))
except Exception:
    sys.exit(0)

nome        = agent.get("nome", "?")
tier        = agent.get("tier", 1)
evolution   = agent.get("evolution", "Stable")
sr          = float(agent.get("success_rate", 100))
pontos      = agent.get("pontos", {})
ext         = pontos.get("externos", 0)
int_        = pontos.get("internos", 0)

# Localização do ledger — resolve relativo ao JSON do agente
ledger_path = agent_path.parent.parent.parent / "project_ledger" / "agent_ledger.log"

ts_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ─── 1. Transição de estado evolutivo ─────────────────────────────────────────

expected = compute_evolution(sr)

if expected != evolution:
    # Aplica a transição diretamente no JSON (sem passar pelo Edit/Write tool)
    agent["evolution"] = expected
    agent_path.write_text(json.dumps(agent, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[HOOK EVOLUCAO] {nome}: {evolution} -> {expected} (sr={sr}%)")

    # Registra no ledger
    if ledger_path.exists():
        append_ledger({
            "ts":           ts_now,
            "type":         "EVOLUCAO",
            "agent":        nome,
            "from":         evolution,
            "to":           expected,
            "success_rate": sr,
            "trigger":      "hook_automatico",
        }, ledger_path)

    evolution = expected  # atualiza variável local

# ─── 2. Aviso de pontos abaixo do threshold do tier ───────────────────────────

THRESHOLDS = {2: (50, 20), 3: (150, 60), 4: (400, 150)}
if tier in THRESHOLDS:
    min_ext, min_int = THRESHOLDS[tier]
    if ext < min_ext or int_ < min_int:
        print(
            f"[HOOK EVOLUCAO] {nome} (Tier {tier}): "
            f"pontos abaixo do threshold — "
            f"atual={ext}ext/{int_}int | mínimo={min_ext}ext/{min_int}int"
        )

sys.exit(0)
