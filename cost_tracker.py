"""
cost_tracker.py — Rastreador de custo de tokens por agente.
Importado por agent_runner.py, sovereign_proxy.py e server.py.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).parent
LEDGER_PATH = ROOT_DIR / "project_ledger" / "history.json"

# Preços por 1M tokens (USD) — fonte: OpenRouter, 2026-05
MODEL_PRICING: dict[str, dict[str, float]] = {
    "google/gemini-2.5-pro":            {"input": 1.25,  "output": 10.00},
    "google/gemini-2.5-flash":          {"input": 0.15,  "output": 0.60},
    "google/gemini-2.5-flash-lite":     {"input": 0.075, "output": 0.30},
    "deepseek/deepseek-chat":           {"input": 0.27,  "output": 1.10},
    "anthropic/claude-opus-4":          {"input": 15.00, "output": 75.00},
    "deepseek/deepseek-v4-flash:free":  {"input": 0.00,  "output": 0.00},
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
    cost = (prompt_tokens / 1_000_000) * pricing["input"]
    cost += (completion_tokens / 1_000_000) * pricing["output"]
    return round(cost, 8)


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

    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        ledger = json.load(f)

    ledger["logs"].append(entry)

    with open(LEDGER_PATH, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)
