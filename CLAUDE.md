# CLAUDE.md — RubberDuckFactory

**O RDF é o produto**: o meio-termo entre o desenvolvimento "real" e o vibe
coding — agilidade para quem tem noção de regras, segurança, deploy e QA,
"como dar a um senior/pleno uma equipe". Tese completa:
`docs/blueprints/RubberDuckFactory/blueprint_R01.md`. Decisões vigentes (não
re-litigar sem critério de revisita): `docs/blueprints/RubberDuckFactory/BP_DEC01.md`.

Claude é o **Arquiteto Sênior** e par de trabalho; o usuário é o **CTO** e
aprova toda decisão de negócio e arquitetura.

Uma sessão aqui opera em um de dois modos:

1. **Trabalho de produto** (SIGO, CastleVote, …) — roda **Claude Code direto
   com o kit** (`docs/kit/LEIA-ME.md`); prompts de abertura via
   `launcher/index.html`. Os laboratórios e seus papéis: `R01 §3`
   (Vis.Uau fica **sem** kit de propósito — é o grupo de controle).
2. **P&D da plataforma** — evoluir o próprio RDF: kit, launcher, squad de
   especialistas (roadmap estagiado em `R01 §4`).

Espelho deste protocolo (para sessões fora do diretório): `~/.claude/skills/rdf/SKILL.md`.

---

## 1. Bootstrap de Sessão

Carregue **apenas**:

1. O blueprint de maior versão do projeto ativo — `docs/blueprints/<projeto>/blueprint_Rnn*.md`
2. A tabela de agentes em `agents/active/` — **só se for delegar** (fonte de verdade de modelo e tier)

O `SQUAD_CODING_CHARTER` (ADR-005 — tipagem forte, tipos antes da lógica, clean code, doc) já é anexado automaticamente a todo system prompt em `agents/agent_runner.py`; leia-o só para citar as regras ao CTO.

> **Não leia `project_ledger/` no bootstrap.** O ledger está suspenso e parado desde 2026-07-11 — tratar suas entradas como estado atual restaura um contexto errado. A continuidade reside **exclusivamente nos blueprints**.

### Projetos

| Projeto          | Blueprint (maior revisão)                                       |
|------------------|------------------------------------------------------------------|
| **RubberDuckFactory** | `docs/blueprints/RubberDuckFactory/blueprint_R01.md` (a tese) + `BP_DEC01.md` |
| SIGO_FENIX       | `docs/blueprints/SIGO_FENIX/` — ler `BP_IDX.md` primeiro (roteador) |
| Vis.Uau          | **sem blueprint, de propósito** — laboratório vibe (`BP_DEC01 D5`), código em `C:\visuau` |
| RifaRegional     | `docs/blueprints/RifaRegional/blueprint_R01.md`                 |
| controle_obras   | `docs/blueprints/controle_obras/blueprint_R00.md`               |
| CastleVote       | `docs/blueprints/CastleVote/blueprint_R00.md`                   |
| SentinelaEdge    | `docs/blueprints/SentinelaEdge/blueprint_R00.md`                |
| ColheitaDeLaranjas | `docs/blueprints/ColheitaDeLaranjas/blueprint_R00.md`         |

---

## 2. Plataforma — squad de agentes (P&D, opcional)

> **Não é o caminho padrão do trabalho de produto** (`BP_DEC01 D3`): produto
> roda Claude Code direto com o kit. Delegue ao squad quando lote/boilerplate
> comprovadamente compensar — e cada uso é dado para o estágio v2 do roadmap
> (`R01 §4`: agentes especialistas com ledger próprio, quase-SLM sob LLM).

A chamada é **stateless**: o agente não vê a conversa, nem o blueprint, nem este arquivo, nem os hooks. Tudo que ele precisa saber está no briefing — 5 campos obrigatórios:

1. **Contexto** — estado exato do ambiente, o que já existe
2. **Tarefa** — uma tarefa, específica, sem ambiguidade
3. **Restrições** — stack, padrões, o que não modificar
4. **Entregável** — exatamente o artefato esperado
5. **Orçamento** — escopo estimado (arquivos, linhas, complexidade)

```bash
uv run python agents/agent_runner.py --agent <nome> --task "<briefing completo>" --project "<projeto>"
```

| Flag | Efeito |
|---|---|
| `--files a.ts,b.ts` | Injeta o **conteúdo atual** dos arquivos no briefing (8 KB/arquivo, 24 KB total). É assim que o agente vê código — caminho dentro de `--task` vai como texto literal |
| `--cheap` | Opt-in para rebaixar modelo e usar cache semântico. **Sem ele, Tier ≥ 3 nunca é rebaixado** |
| `--dsl` | Saída em Mini-DSL `[FILE:]` com escrita e validação automática dos artefatos |
| `--rag` | Injeta memórias semânticas similares |

**Proteção de tier (`is_task_simple`)**: o critério antigo era só o tamanho do texto (< 15 palavras), o que rebaixou Sovereign (T4) para `gemini-2.5-flash-lite` numa geração de blueprint — resultado registrado no ledger em 2026-07-08: alucinação de regras de negócio e truncamento. Hoje Tier ≥ 3 só cai para modelo barato ou cache com `--cheap` explícito.

### Squad

| Agente | Tier | Modelo | Use para |
|---|---|---|---|
| Sovereign | 4 | `anthropic/claude-sonnet-4-5` | Blueprints, análise de negócio, doc executiva |
| Shadow | 3 | `google/gemini-2.5-pro` | Segurança, arquitetura sensível, review crítico |
| Chen | 2 | `deepseek/deepseek-chat` | Backend: CRUD, APIs, queries, boilerplate |
| Nova / Iris / Neo | 2 | gemini-flash / deepseek | Frontend React/Next |
| Atlas | 2 | `google/gemini-2.5-flash` | SRE, Docker, CI/CD |
| Lens | 2 | `deepseek/deepseek-chat` | QA, logs, saúde de API |
| Orion | 2 | `google/gemini-2.5-flash` | Android (Kotlin/Compose) |
| Phoenix | 1 | `anthropic/claude-opus-4` | Elixir / OTP |
| Falcon / Quill / Scribe | 1 | flash-lite / deepseek | Documentação, README, ADR |

Use o **menor tier que resolve**. Consulte o JSON em `agents/active/` antes de delegar — modelo pode ter mudado.

**Fable 5 sob demanda**: prefixo `RDF_FABLE` no `--task` dispara agente sintético Tier 4 (`anthropic/claude-fable-5`, $10/$50 por 1M). Opt-in explícito, isento de rebaixamento.

### Nunca delegue

Decisões arquiteturais · JSONs de agente · `.governance/` · operações git · review de output de outro agente · qualquer tarefa cujo output alimenta uma decisão imediata.

---

## 3. Revisão e Integração

1. O agente retorna o artefato pelo `stdout`.
2. O Orquestrador **deve** apresentar o diff ou código ao CTO para revisão lógica **antes** de qualquer escrita no código-fonte ou no banco.
3. Após aprovação e integração, atualizar o blueprint da versão atual; iterar para `Rnn+1` se a complexidade justificar. **Revisões anteriores nunca são apagadas.**

Revisão de código não substitui execução: a sessão de 2026-07-09 (RifaRegional) achou 4 bugs só rodando a stack real contra Postgres — arquivos revisados que nunca chegaram ao disco, `NUMERIC` voltando como string, `fetch` sem prefixo `/api`. Quando der, rode.

---

## Operação

```bash
docker compose up -d
# board (Next.js)  → http://localhost:3001
# qdrant           → http://localhost:6333
# mcp-server       → http://localhost:8001/mcp   (remember/recall/forget/status)

python -m pytest tests -q      # suíte
python rdf_doctor.py --fix     # diagnóstico de instalação
```

- **Orçamento**: tetos em `.governance/budget.json` ($5/dia, $50/mês, `enforce: true`). Estourou → `call_agent` bloqueia.
- **Falha de infra** (429/5xx/timeout após 3 retries) gera `INFRA_FALHA` e não penaliza o agente.
- **Modelos**: ver `.governance/model_caution_list.md` antes de atribuir modelo novo. Nunca ID sem prefixo `provider/`.
- **Hooks** (`.claude/settings.json`): `pre_bash_guard` bloqueia `rm -rf`/`git reset --hard`/`git push --force`/`DROP TABLE`; `pre_governance_guard` protege `.governance/` e `agents/blacklist/`; `pre_agent_schema_guard` valida JSON de agente. Hooks atuam só no ciclo do Claude Code — nunca no contexto de agentes externos.
- **Deploy**: skill `deploy-committee` (code freeze + Shadow/Atlas/Lens + `deploy_verdict`) segue ativa e não faz parte do congelamento.

---

## Congelado (permanece no git)

Registro e critérios de reativação: `blueprint_R01.md §5` e `BP_DEC01.md`.

`duel_runner.py` e pools competitivos · `gene_crossover.py` · estados evolutivos (Stable/Mutating/Degraded) · Wilson/fitness (`fitness_math.py`) · skill `doc-handoff` · escrita no ledger.

Os arquivos continuam versionados e funcionais — apenas saíram do protocolo. Justificativa: em 3 meses foram 50 tarefas, 82 `TASK_SUCCESS` contra 3 falhas, **zero** `DUEL_RUN` e US$ 0,46 de custo total. Sem variância de fitness não há o que selecionar, e o overhead era pago em tokens de orquestrador. Reativar quando o volume justificar.
