#!/usr/bin/env python3
"""
agents/agent_runner.py — Runner de Agentes do Squad RubberDuckFactory
Carrega cada agente ativo, envia uma mensagem via OpenRouter e exibe:
  nome + modelo + resposta "hello world" do próprio agente.

Uso: uv run python agents/agent_runner.py
"""

import os
import json
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from cost_tracker import record_cost

# ─── Configuração ─────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.parent
AGENTS_DIR = ROOT_DIR / "agents" / "active"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

load_dotenv(ROOT_DIR / ".env")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

if not OPENROUTER_API_KEY:
    raise SystemExit(
        "❌ OPENROUTER_API_KEY não encontrada no .env\n"
        "   Preencha o arquivo .env com: OPENROUTER_API_KEY=sk-or-v1-..."
    )


def load_agents() -> list[dict]:
    """Carrega todos os agentes .json da pasta agents/active/."""
    agents = []
    for path in sorted(AGENTS_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            agent = json.load(f)
        agent["_file"] = path.name
        agents.append(agent)
    return agents


def call_agent(agent: dict) -> dict:
    """
    Envia ao agente a instrução de se apresentar com nome, modelo e hello world.
    Retorna dict com 'content', 'prompt_tokens' e 'completion_tokens'.
    """
    system_prompt = agent.get("system_prompt", "")
    model = agent.get("model", "deepseek/deepseek-chat")
    nome = agent.get("nome", "Agente")

    user_message = (
        f"Apresente-se em uma única mensagem curta contendo exatamente: "
        f"seu nome ({nome}), o modelo de LLM que você usa ({model}) e um 'Hello World'. "
        f"Seja direto e objetivo."
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/Huilgner/RubberDuckFactory",
        "X-Title": "RubberDuckFactory - Agent Runner",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
        "max_tokens": 256,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(OPENROUTER_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            usage = data.get("usage", {})
            return {
                "content": data["choices"][0]["message"]["content"].strip(),
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            }
    except httpx.HTTPStatusError as e:
        return {"content": f"❌ Erro HTTP {e.response.status_code}: {e.response.text}", "prompt_tokens": 0, "completion_tokens": 0}
    except httpx.RequestError as e:
        return {"content": f"❌ Erro de conexão: {e}", "prompt_tokens": 0, "completion_tokens": 0}
    except (KeyError, IndexError) as e:
        return {"content": f"❌ Resposta inesperada da API: {e}", "prompt_tokens": 0, "completion_tokens": 0}


def main():
    print("=" * 60)
    print("  🦆 AGENT RUNNER — RubberDuckFactory Squad")
    print("  Testando: nome + modelo + hello world de cada agente")
    print("=" * 60)
    print()

    agents = load_agents()

    if not agents:
        print("⚠️  Nenhum agente encontrado em agents/active/")
        return

    for agent in agents:
        nome = agent.get("nome", "?")
        model = agent.get("model", "?")
        status = agent.get("status", "?")
        tier = agent.get("tier", "?")

        print(f"{'─' * 60}")
        print(f"🤖 Agente  : {nome}")
        print(f"   Modelo  : {model}")
        print(f"   Status  : {status} | Tier {tier}")
        print(f"   Arquivo : {agent['_file']}")
        print()
        print(f"⏳ Chamando {nome} via OpenRouter...")
        print()

        resultado = call_agent(agent)
        resposta = resultado["content"]
        prompt_tokens = resultado["prompt_tokens"]
        completion_tokens = resultado["completion_tokens"]

        record_cost(
            agent=nome,
            model=model,
            task="hello_world",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        print(f"💬 Resposta de {nome}:")
        print(f"   {resposta}")
        print(f"   📊 Tokens: {prompt_tokens} in / {completion_tokens} out")
        print()

    print("=" * 60)
    print("✅ Todos os agentes responderam.")
    print("=" * 60)


if __name__ == "__main__":
    main()
