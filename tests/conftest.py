"""Fixtures compartilhadas da suíte de testes do RubberDuckFactory."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agents"))


@pytest.fixture
def sandbox_ledger(tmp_path, monkeypatch):
    """Redireciona toda escrita de ledger/orçamento para um diretório temporário."""
    import ledger_io
    import cost_tracker

    monkeypatch.setattr(ledger_io, "LEDGER_DIR", tmp_path)
    monkeypatch.setattr(ledger_io, "HISTORY_JSONL", tmp_path / "history.jsonl")
    monkeypatch.setattr(ledger_io, "HISTORY_JSON", tmp_path / "history.json")
    monkeypatch.setattr(ledger_io, "LOCK_FILE", tmp_path / ".history.lock")
    monkeypatch.setattr(cost_tracker, "BUDGET_PATH", tmp_path / "budget.json")
    monkeypatch.setattr(cost_tracker, "BUDGET_STATE_PATH", tmp_path / "budget_state.json")
    return tmp_path
