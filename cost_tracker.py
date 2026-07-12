"""
cost_tracker.py — Rastreador de custo de tokens por agente + guardrail de orçamento.
Importado por agent_runner.py, sovereign_proxy.py e server.py.

Orçamento (governance-as-code): tetos em .governance/budget.json; gasto corrente
em project_ledger/budget_state.json (local, gitignored). assert_budget_ok() deve
ser chamado ANTES de qualquer chamada de LLM — estourou o teto, bloqueia.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from ledger_io import append_history, history_lock

ROOT_DIR = Path(__file__).parent
LEDGER_PATH = ROOT_DIR / "project_ledger" / "history.json"
BUDGET_PATH = ROOT_DIR / ".governance" / "budget.json"
BUDGET_STATE_PATH = ROOT_DIR / "project_ledger" / "budget_state.json"


class BudgetExceededError(Exception):
    """Teto de orçamento diário ou mensal atingido."""

# Preços por 1M tokens (USD) — fonte: OpenRouter /api/v1/models, 2026-06-10
MODEL_PRICING: dict[str, dict[str, float]] = {
    # Google Gemini
    "google/gemini-2.5-pro":            {"input": 1.25,  "output": 10.00},
    "google/gemini-2.5-flash":          {"input": 0.30,  "output": 2.50},
    "google/gemini-2.5-flash-lite":     {"input": 0.10,  "output": 0.40},
    "google/gemini-3.1-flash-lite":     {"input": 0.25,  "output": 1.50},
    "google/gemini-3-flash-preview":    {"input": 0.50,  "output": 3.00},
    "google/gemini-3.5-flash":          {"input": 1.50,  "output": 9.00},
    # DeepSeek
    "deepseek/deepseek-chat":           {"input": 0.20,  "output": 0.80},
    "deepseek/deepseek-v4-flash":       {"input": 0.10,  "output": 0.20},
    "deepseek/deepseek-v4-flash:free":  {"input": 0.00,  "output": 0.00},
    "deepseek/deepseek-v4-pro":         {"input": 0.43,  "output": 0.87},
    # MiniMax
    "minimax/minimax-m2":               {"input": 0.26,  "output": 1.00},
    "minimax/minimax-m2.5":             {"input": 0.15,  "output": 0.90},
    "minimax/minimax-m3":               {"input": 0.30,  "output": 1.20},
    # Anthropic
    "anthropic/claude-opus-4":          {"input": 15.00, "output": 75.00},
    "anthropic/claude-sonnet-4-5":      {"input": 3.00,  "output": 15.00},
    "anthropic/claude-fable-5":         {"input": 10.00, "output": 50.00},
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
    cost = (prompt_tokens / 1_000_000) * pricing["input"]
    cost += (completion_tokens / 1_000_000) * pricing["output"]
    return round(cost, 8)


def _load_budget() -> dict:
    try:
        return json.loads(BUDGET_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_budget_state(now: datetime) -> dict:
    day, month = now.strftime("%Y-%m-%d"), now.strftime("%Y-%m")
    state = {}
    if BUDGET_STATE_PATH.exists():
        try:
            state = json.loads(BUDGET_STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    # vira o dia/mes: zera o contador correspondente
    if state.get("day") != day:
        state["day"], state["day_spent_usd"] = day, 0.0
    if state.get("month") != month:
        state["month"], state["month_spent_usd"] = month, 0.0
    return state


def _add_spend(cost_usd: float) -> None:
    """Acumula gasto no estado de orçamento (sob o mesmo lock do histórico)."""
    with history_lock():
        state = _load_budget_state(datetime.now(timezone.utc))
        state["day_spent_usd"] = round(state.get("day_spent_usd", 0.0) + cost_usd, 8)
        state["month_spent_usd"] = round(state.get("month_spent_usd", 0.0) + cost_usd, 8)
        BUDGET_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BUDGET_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def assert_budget_ok() -> None:
    """
    Levanta BudgetExceededError se o teto diário ou mensal foi atingido
    (com enforce=true em .governance/budget.json). Sem arquivo de budget,
    não bloqueia nada.
    """
    budget = _load_budget()
    if not budget:
        return
    state = _load_budget_state(datetime.now(timezone.utc))
    day_spent = float(state.get("day_spent_usd", 0.0))
    month_spent = float(state.get("month_spent_usd", 0.0))
    daily_cap = float(budget.get("daily_usd", 0) or 0)
    monthly_cap = float(budget.get("monthly_usd", 0) or 0)

    exceeded = None
    if daily_cap and day_spent >= daily_cap:
        exceeded = f"teto DIARIO atingido: ${day_spent:.4f} / ${daily_cap:.2f}"
    elif monthly_cap and month_spent >= monthly_cap:
        exceeded = f"teto MENSAL atingido: ${month_spent:.4f} / ${monthly_cap:.2f}"
    if not exceeded:
        return

    msg = f"{exceeded} (.governance/budget.json). Ajuste o teto ou aguarde a virada do periodo."
    if budget.get("enforce", True):
        append_history({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "BUDGET_BLOCK",
            "reason": exceeded,
        })
        raise BudgetExceededError(msg)
    print(f"  [ORCAMENTO][AVISO] {msg}")


def record_cost(
    agent: str,
    model: str,
    task: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> None:
    cost_usd = calculate_cost(model, prompt_tokens, completion_tokens)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "COST_RECORD",
        "agent": agent,
        "model": model,
        "task": task,
        "tokens": {
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": prompt_tokens + completion_tokens,
        },
        "cost_usd": cost_usd,
    }

    append_history(entry)
    if cost_usd > 0:
        _add_spend(cost_usd)
