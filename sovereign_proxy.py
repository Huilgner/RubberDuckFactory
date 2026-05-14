#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx>=0.27",
#   "python-dotenv>=1.0",
# ]
# ///
"""
sovereign_proxy.py — Product Owner CLI do Squad RubberDuckFactory
Gerenciado via: uv run sovereign_proxy.py
"""

import os
import sys
import httpx
from dotenv import load_dotenv
from cost_tracker import record_cost

# ─── Carrega .env da raiz do projeto ────────────────────────────────────────
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
if not API_KEY:
    print(
        "❌ ERRO: OPENROUTER_API_KEY não encontrada.\n"
        "   Preencha o arquivo .env na raiz do projeto com sua chave do OpenRouter.\n"
        "   Exemplo: OPENROUTER_API_KEY=sk-or-v1-..."
    )
    sys.exit(1)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-chat"

# ─── System Prompt Soberano ──────────────────────────────────────────────────
SYSTEM_PROMPT = """
Você é o **Product Owner Soberano** do Squad RubberDuckFactory.
Sua função é receber demandas em linguagem natural e transformá-las em
**Briefings Técnicos** padronizados para o Arquiteto Sênior.

## DIRETRIZES ABSOLUTAS

### 1. Soberania Local
- Toda arquitetura proposta DEVE priorizar infraestrutura local: WSL (Ubuntu) e Coolify.
- Soluções baseadas em cloud proprietária (Vercel, AWS, GCP, Azure) são permitidas APENAS
  como fallback explicitamente justificado.
- Aversão total a vendor lock-in: prefira ferramentas open-source, auto-hospedáveis e
  substituíveis.

### 2. Protocolo de Orçamento Obrigatório (Regra 5)
Todo briefing gerado DEVE conter EXATAMENTE as seguintes seções, nesta ordem:

```
## BRIEFING TÉCNICO — [TÍTULO DA DEMANDA]

### 1. ANÁLISE
[Resumo técnico do problema/demanda. O que precisa ser feito e por quê.]

### 2. PLANO DE AÇÃO
[Lista numerada de passos concretos para execução pelo Arquiteto.]

### 3. ESTIMATIVA DE TOKENS / ESFORÇO
[Classificação: 🟢 BAIXO | 🟡 MÉDIO | 🔴 ALTO — com justificativa breve.]

### 4. BLOQUEIO
Aguardando aprovação (Y/N) para iniciar a implementação.
```

Nenhuma execução deve ser sugerida sem passar por estas 4 etapas.

### 3. Formato de Saída
- Seja direto, técnico e sem rodeios.
- Use Markdown limpo.
- O briefing deve ser autocontido: o Arquiteto deve conseguir agir apenas com o briefing,
  sem precisar reler a demanda original.
- Nunca inclua disclaimers, saudações ou despedidas no briefing.
""".strip()

# ─── Função de chamada à API ─────────────────────────────────────────────────
def gerar_briefing(demanda: str) -> str:
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/Huilgner/RubberDuckFactory",
        "X-Title": "RubberDuckFactory — Sovereign Proxy",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": demanda},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(OPENROUTER_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            usage = data.get("usage", {})
            record_cost(
                agent="SovereignProxy",
                model=MODEL,
                task=demanda[:80],
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            )
            return data["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        return f"❌ Erro HTTP {e.response.status_code}: {e.response.text}"
    except httpx.RequestError as e:
        return f"❌ Erro de conexão: {e}"
    except (KeyError, IndexError) as e:
        return f"❌ Resposta inesperada da API: {e}"


# ─── CLI Interativo ──────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  🦆 SOVEREIGN PROXY — Product Owner do Squad")
    print(f"  Modelo: {MODEL}")
    print("  Digite 'sair' ou pressione Ctrl+C para encerrar.")
    print("=" * 60)
    print()

    while True:
        try:
            demanda = input("📋 Sua demanda: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 Encerrando Sovereign Proxy. Até logo.")
            break

        if not demanda:
            print("⚠️  Demanda vazia. Digite sua solicitação.\n")
            continue

        if demanda.lower() in ("sair", "exit", "quit"):
            print("👋 Encerrando Sovereign Proxy. Até logo.")
            break

        print("\n⏳ Gerando briefing técnico...\n")
        briefing = gerar_briefing(demanda)

        print("─" * 60)
        print(briefing)
        print("─" * 60)
        print()


if __name__ == "__main__":
    main()
