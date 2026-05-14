# Model Caution List — RubberDuckFactory

**Autor:** Quill (baseado em pesquisa externa) | **Data:** 2026-05-14
**Revisão:** Pendente aprovação do Arquiteto (Shadow)

> Lista de modelos e categorias a evitar ou usar com restrições ao inicializar agentes.
> Alimenta o mecanismo de seleção artificial descrito no ADR-003.

---

## Categorias com Alta Taxa de Falha

### 1. Modelos pequenos open-source (< 30B parâmetros)

**Modelos afetados no OpenRouter:**
- `meta-llama/llama-3.2-1b-instruct`
- `meta-llama/llama-3.2-3b-instruct`
- `meta-llama/llama-3.2-3b-instruct:free`
- `google/gemma-3-4b-it`
- `google/gemma-3n-e4b-it`
- `mistralai/mistral-7b-instruct-v0.1`

**Falha principal:** Taxas de alucinação de 80–90% em benchmarks HalluLens/HaluEval (2025).
**Uso permitido:** Apenas tarefas de formatação, transformação de texto estruturado ou parsing — nunca geração de código crítico ou decisões de arquitetura.

---

### 2. Modelos de raciocínio (reasoning mode) em tarefas factuais simples

**Modelos afetados:**
- Variantes `*-thinking`, `*-reasoning`, `*-r1` de qualquer família

**Falha principal:** Paradoxo identificado em benchmarks 2026 — modelos com raciocínio explícito apresentam >10% de alucinação em tarefas factuais básicas, pior que suas versões base. O raciocínio parece amplificar erros em vez de reduzi-los quando o contexto é simples.
**Uso permitido:** Problemas de alta complexidade onde o raciocínio multi-step é necessário. Proibido para lookups simples, validações e documentação.

---

### 3. Gemini 1.5 (família descontinuada)

**Modelos afetados:**
- `gemini-1.5-pro` *(já removido do projeto)*
- `gemini-1.5-flash` *(já removido)*
- `gemini-1.5-flash-8b` *(já removido)*

**Falha principal:** IDs inválidos no OpenRouter — família descontinuada. Registrado como caso histórico: os três agentes originais (Shadow, Nova, Falcon) usavam esses modelos e falhavam silenciosamente com erro 400.
**Status:** Substituídos por `gemini-2.5-pro/flash/flash-lite` respectivamente.

---

### 4. Modelos sem prefixo de provider

**Padrão afetado:** qualquer ID no formato `nome-modelo` sem `provider/`

**Falha principal:** OpenRouter exige o formato `provider/modelo`. IDs curtos retornam 400 silencioso, difícil de diagnosticar.
**Regra:** Todo `model` em JSON de agente DEVE conter `/`. IDs curtos são inválidos por definição neste stack.

---

## Modelos com Ressalvas Específicas

| Modelo | Ressalva | Fonte |
|---|---|---|
| `google/gemini-3-pro-*` | 76% de alucinação em cenários de Q&A com fontes (estudo BBC/EBU 2026) | HalluLens benchmark |
| `meta-llama/llama-3.1-8b-instruct` | Contexto limitado (16K), performance de código abaixo de modelos maiores da mesma família | SWE-bench / CodeSOTA |
| `mistralai/mistral-7b-instruct-v0.1` | Contexto de apenas 2.8K tokens — inviável para tarefas de código com contexto longo | OpenRouter metadata |
| Modelos `*:free` em geral | Sujeitos a rate limit de provider upstream (Venice, etc.) — instáveis para uso em produção | Observado em produção (Quill/qwen3-coder) |

---

## Modelos Recomendados por Tier

| Tier | Clearance | Modelos indicados |
|---|---|---|
| 1 — Observer | Tarefas simples, docs, formatação | `google/gemini-2.5-flash-lite`, `deepseek/deepseek-v4-flash:free` |
| 2 — Operator | Desenvolvimento, frontend, backend | `google/gemini-2.5-flash`, `deepseek/deepseek-chat` |
| 3 — Specialist | Arquitetura, segurança, decisões críticas | `google/gemini-2.5-pro`, `anthropic/claude-opus-4` |
| 4 — Architect | *(reservado)* | A definir com base em dados do ledger |

---

## Fontes

- HalluLens Benchmark (ACL 2025): avaliação de alucinação resistente a data contamination
- Vectara Hallucination Leaderboard 2026: comparativo cross-model
- BBC/EBU Study 2026: alucinação em Q&A com fontes jornalísticas
- CodeSOTA / SWE-bench: qualidade de geração de código
- Observações internas do projeto (ledger + agent_runner)
