"""cost_tracker: guardrail de orçamento."""
import json

import pytest

import cost_tracker as ct
import ledger_io


def _set_budget(sandbox, **kwargs):
    (sandbox / "budget.json").write_text(json.dumps(kwargs), encoding="utf-8")


def test_no_budget_file_never_blocks(sandbox_ledger):
    ct.assert_budget_ok()  # não deve levantar


def test_blocks_when_daily_cap_reached(sandbox_ledger):
    _set_budget(sandbox_ledger, daily_usd=0.01, monthly_usd=1.0, enforce=True)
    ct.assert_budget_ok()
    ct._add_spend(0.005)
    ct.assert_budget_ok()  # abaixo do teto
    ct._add_spend(0.006)
    with pytest.raises(ct.BudgetExceededError):
        ct.assert_budget_ok()
    # evento auditável gravado
    assert any(e["type"] == "BUDGET_BLOCK" for e in ledger_io.read_history())


def test_enforce_false_only_warns(sandbox_ledger):
    _set_budget(sandbox_ledger, daily_usd=0.01, enforce=False)
    ct._add_spend(0.02)
    ct.assert_budget_ok()  # avisa mas não levanta


def test_day_rollover_resets_counter(sandbox_ledger):
    _set_budget(sandbox_ledger, daily_usd=0.01, enforce=True)
    ct._add_spend(0.02)
    # simula estado de ontem: o rollover deve zerar o contador diário
    state = json.loads((sandbox_ledger / "budget_state.json").read_text(encoding="utf-8"))
    state["day"] = "2000-01-01"
    (sandbox_ledger / "budget_state.json").write_text(json.dumps(state), encoding="utf-8")
    from datetime import datetime, timezone
    fresh = ct._load_budget_state(datetime.now(timezone.utc))
    assert fresh["day_spent_usd"] == 0.0
