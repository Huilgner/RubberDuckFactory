import os
import sys
from datetime import datetime

LOG_PATH = r"C:\RubberDuckFactory\project_ledger\hooks_audit.log"
TS_PATH = r"C:\RubberDuckFactory\.claude\hooks\.last_stop_ts"

now = datetime.now()

last_ts = None
if os.path.exists(TS_PATH):
    try:
        with open(TS_PATH, "r", encoding="utf-8") as f:
            last_ts = f.read().strip()
    except Exception:
        pass

entries = []
if os.path.exists(LOG_PATH):
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ts = line.split(" | ")[0] if " | " in line else ""
                if last_ts is None or ts > last_ts:
                    entries.append(line)
    except Exception:
        pass

try:
    os.makedirs(os.path.dirname(TS_PATH), exist_ok=True)
    with open(TS_PATH, "w", encoding="utf-8") as f:
        f.write(now.isoformat())
except Exception:
    pass

if entries:
    print(f"[DIGEST] {len(entries)} op(s) neste turno:")
    for e in entries:
        parts = e.split(" | ")
        if len(parts) >= 3:
            print(f"  {parts[1]}: {parts[2][:80]}")
        else:
            print(f"  {e[:100]}")

sys.exit(0)
