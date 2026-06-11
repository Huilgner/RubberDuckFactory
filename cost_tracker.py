"""
cost_tracker.py — Rastreador de custo de tokens por agente.
Importado por agent_runner.py, sovereign_proxy.py e server.py.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).parent
LEDGER_PATH = ROOT_DIR / "project_ledger" / "history.json"

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
