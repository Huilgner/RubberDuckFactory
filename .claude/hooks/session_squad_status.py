import json
import sys
from pathlib import Path

agents_dir = Path(r"C:\RubberDuckFactory\agents\active")
lines = []

for agent_file in sorted(agents_dir.glob("*.json")):
    try:
        agent = json.loads(agent_file.read_text(encoding="utf-8"))
        nome = agent.get("nome", agent_file.stem)
        tier = agent.get("tier", "?")
        evolution = agent.get("evolution", "?")
        ext = agent.get("pontos", {}).get("externos", 0)
        int_ = agent.get("pontos", {}).get("internos", 0)
        flag = " [MUTATING]" if evolution == "Mutating" else ""
        lines.append(f"  {nome} (T{tier}) | {evolution}{flag} | {ext}ext / {int_}int")
    except Exception:
        pass

if lines:
    print("=== SQUAD STATUS ===")
    for line in lines:
        print(line)
    print("====================")

sys.exit(0)
