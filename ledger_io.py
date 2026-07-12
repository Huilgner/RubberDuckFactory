"""
ledger_io.py — Escrita segura e concorrente no histórico do RubberDuckFactory.
Importado por cost_tracker.py, agent_runner.py, duel_runner.py, gene_crossover.py,
self_healing_deploy.py e inter_agent_negotiation.py.

Fonte de verdade: project_ledger/history.jsonl (append-only, 1 evento JSON por linha).
Visão de compatibilidade: project_ledger/history.json ({"logs": [...]}) rematerializada
atomicamente a cada escrita, para os leitores existentes (board, server.py,
sync_history.py, quality_gate_server.py).

Toda escrita passa por um lock de arquivo entre processos (msvcrt no Windows,
fcntl no POSIX). Isso elimina o cenário em que duel_runner (modo parallel) e
agent_runner reescrevem o history.json ao mesmo tempo e uma escrita engole a outra —
violando a premissa de ledger imutável.
"""

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

ROOT_DIR      = Path(__file__).parent
LEDGER_DIR    = ROOT_DIR / "project_ledger"
HISTORY_JSONL = LEDGER_DIR / "history.jsonl"
HISTORY_JSON  = LEDGER_DIR / "history.json"
LOCK_FILE     = LEDGER_DIR / ".history.lock"

LOCK_TIMEOUT_S = 15.0

if os.name == "nt":
    import msvcrt

    def _try_lock(fh) -> None:
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock(fh) -> None:
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def _try_lock(fh) -> None:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(fh) -> None:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


@contextmanager
def history_lock(timeout: float = LOCK_TIMEOUT_S):
    """Lock exclusivo entre processos para escrita no histórico."""
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    fh = open(LOCK_FILE, "a+", encoding="utf-8")
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                _try_lock(fh)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"Nao foi possivel adquirir o lock do historico ({LOCK_FILE}) em {timeout}s"
                    )
                time.sleep(0.1)
        yield
    finally:
        try:
            _unlock(fh)
        except OSError:
            pass
        fh.close()


def _seed_jsonl_from_legacy() -> None:
    """Migra o history.json legado para history.jsonl na primeira escrita (uma vez só)."""
    if HISTORY_JSONL.exists() or not HISTORY_JSON.exists():
        return
    try:
        logs = json.loads(HISTORY_JSON.read_text(encoding="utf-8")).get("logs", [])
    except Exception:
        return
    with open(HISTORY_JSONL, "w", encoding="utf-8") as f:
        for entry in logs:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def append_history(entry: dict) -> None:
    """
    Registra um evento no histórico (append-only, sob lock).

    1. Anexa a entrada em history.jsonl (fonte de verdade).
    2. Rematerializa history.json atomicamente (tmp + os.replace) para
       manter os leitores legados funcionando sem alteração.
    """
    with history_lock():
        _seed_jsonl_from_legacy()

        with open(HISTORY_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        data: dict = {}
        if HISTORY_JSON.exists():
            try:
                loaded = json.loads(HISTORY_JSON.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    data = loaded
            except Exception:
                data = {}
        data.setdefault("logs", []).append(entry)

        tmp = HISTORY_JSON.with_name(HISTORY_JSON.name + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, HISTORY_JSON)


def read_history() -> list[dict]:
    """Lê todos os eventos do histórico. Prefere o JSONL; cai para o JSON legado."""
    if HISTORY_JSONL.exists():
        events = []
        for line in HISTORY_JSONL.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return events
    if HISTORY_JSON.exists():
        try:
            return json.loads(HISTORY_JSON.read_text(encoding="utf-8")).get("logs", [])
        except Exception:
            return []
    return []
