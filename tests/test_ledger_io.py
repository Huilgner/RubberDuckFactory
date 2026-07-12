"""ledger_io: escrita básica, migração do legado, visão de compatibilidade e concorrência."""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import ledger_io


def test_append_and_read(sandbox_ledger):
    ledger_io.append_history({"type": "TEST", "n": 1})
    ledger_io.append_history({"type": "TEST", "n": 2})
    events = ledger_io.read_history()
    assert [e["n"] for e in events] == [1, 2]


def test_legacy_migration_and_compat_view(sandbox_ledger):
    legacy = {"logs": [{"type": "LEGACY", "n": 1}, {"type": "LEGACY", "n": 2}]}
    (sandbox_ledger / "history.json").write_text(json.dumps(legacy), encoding="utf-8")

    ledger_io.append_history({"type": "NEW", "n": 3})

    events = ledger_io.read_history()
    assert len(events) == 3 and events[0]["type"] == "LEGACY"
    # visão de compatibilidade continua parseável e completa
    view = json.loads((sandbox_ledger / "history.json").read_text(encoding="utf-8"))
    assert len(view["logs"]) == 3


def test_concurrent_threads(sandbox_ledger):
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda i: ledger_io.append_history({"type": "T", "i": i}), range(80)))
    events = ledger_io.read_history()
    assert len(events) == 80
    # jsonl íntegro: toda linha é JSON válido
    lines = (sandbox_ledger / "history.jsonl").read_text(encoding="utf-8").splitlines()
    assert len([json.loads(l) for l in lines if l.strip()]) == 80


def test_concurrent_processes(sandbox_ledger, tmp_path):
    """Dois processos reais escrevendo ao mesmo tempo: nada se perde nem corrompe."""
    script = tmp_path / "worker.py"
    script.write_text(
        f"""
import sys
sys.path.insert(0, {str(Path(__file__).parent.parent)!r})
import ledger_io
from pathlib import Path
base = Path({str(sandbox_ledger)!r})
ledger_io.LEDGER_DIR = base
ledger_io.HISTORY_JSONL = base / "history.jsonl"
ledger_io.HISTORY_JSON = base / "history.json"
ledger_io.LOCK_FILE = base / ".history.lock"
wid = int(sys.argv[1])
for i in range(20):
    ledger_io.append_history({{"type": "P", "worker": wid, "i": i}})
""",
        encoding="utf-8",
    )
    procs = [subprocess.Popen([sys.executable, str(script), str(w)]) for w in range(2)]
    assert all(p.wait(timeout=60) == 0 for p in procs)
    events = [e for e in ledger_io.read_history() if e.get("type") == "P"]
    assert len(events) == 40
