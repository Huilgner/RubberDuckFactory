# Guia do RubberDuckFactory — Como funciona e por quê

> Documento de onboarding para quem vai **testar e entender** o RubberDuckFactory.
> Mais explicativo que o `README.md` (que é a referência rápida). Aqui o foco é o *porquê* de cada peça.

---

## Índice

1. [A ideia em uma frase](#1-a-ideia-em-uma-frase)
2. [O problema que ele resolve](#2-o-problema-que-ele-resolve)
3. [Arquitetura em camadas](#3-arquitetura-em-camadas)
4. [O squad de agentes](#4-o-squad-de-agentes)
5. [Tiers e governança — por que existem](#5-tiers-e-governança--por-que-existem)
6. [As Skills](#6-as-skills)
7. [Os servidores MCP](#7-os-servidores-mcp)
8. [Hooks — guardrails determinísticos](#8-hooks--guardrails-determinísticos)
9. [O Deploy Committee](#9-o-deploy-committee)
10. [Ideias de engenharia diferenciadas](#10-ideias-de-engenharia-diferenciadas)
11. [Como testar — passo a passo](#11-como-testar--passo-a-passo)
12. [FAQ para quem está testando](#12-faq-para-quem-está-testando)

---

## 1. A ideia em uma frase

**O RubberDuckFactory é uma "empresa de software" feita de agentes de IA, onde o Claude é o gerente e delega tarefas a uma equipe de modelos mais baratos — tudo sob um sistema de governança que registra, pune e promove cada agente conforme seu desempenho.**

O nome vem do *rubber duck debugging* (explicar o problema para um patinho de borracha): aqui, em vez de um patinho, você tem um esquadrão de patos especializados.

---

## 2. O problema que ele resolve

Usar um modelo topo de linha (Claude Opus, por exemplo) para **tudo** é caro e desperdiçado: gerar 200 linhas de CRUD repetitivo custa o mesmo por token que uma decisão de arquitetura difícil, mas o valor entregue é totalmente diferente.

A premissa do RDF é **alocação de custo proporcional à complexidade**:

- **Cognição cara** (decidir arquitetura, revisar código, coordenar) fica com o orquestrador (Claude).
- **Trabalho de volume e baixa complexidade** (boilerplate, docs, refatorações simples) vai para modelos baratos (DeepSeek, Gemini Flash).

E como modelos baratos erram mais, o sistema adiciona **governança**: cada agente tem histórico, pontuação e estado evolutivo. Quem erra demais é rebaixado ou demitido. Quem entrega é promovido. Tudo auditável.

> **Princípio central:** *Claude decide, agentes executam.* O orquestrador nunca gera grandes blocos de boilerplate; agentes nunca tomam decisões arquiteturais.

---

## 3. Arquitetura em camadas

```
┌─────────────────────────────────────────────────────────────┐
│  CAMADA 0 — ORQUESTRADOR                                     │
│  Claude Code (rodando localmente). Decide, delega, revisa.  │
│  Carrega skills e conecta nos MCPs via .mcp.json            │
└───────────────┬─────────────────────────────────────────────┘
                │ delega via agent_runner.py
                ▼
┌─────────────────────────────────────────────────────────────┐
│  CAMADA 1 — SQUAD DE AGENTES                                 │
│  12 agentes (JSON em agents/active/). Cada um: modelo,      │
│  tier, especialidade, pontos, estado evolutivo.            │
│  Chamados via OpenRouter (1 API para todos os modelos).    │
└───────────────┬─────────────────────────────────────────────┘
                │ registra tudo
                ▼
┌─────────────────────────────────────────────────────────────┐
│  CAMADA 2 — GOVERNANÇA                                       │
│  .governance/  (regras como código)                         │
│  project_ledger/history.json  (log append-only de eventos)  │
│  Pontos · Infrações · Promoções · Blacklist                │
└─────────────────────────────────────────────────────────────┘

         ╔═══════════════ SERVIÇOS DE APOIO ═══════════════╗
         ║  Qdrant (memória vetorial)   → :6333            ║
         ║  MCP memória (remember/recall) → :8001          ║
         ║  MCP quality-gate (deploy)   → stdio            ║
         ║  Board (dashboard Next.js)   → :3001            ║
         ╚══════════════════════════════════════════════════╝

         ╔═══════════════ GUARDRAILS (HOOKS) ══════════════╗
         ║  Disparam por evento, ANTES do modelo julgar.   ║
         ║  Bloqueiam rm -rf, protegem governança, auditam ║
         ╚══════════════════════════════════════════════════╝
```

**Por que em camadas?** Separação de responsabilidades. O orquestrador não sabe (nem precisa saber) como cada agente é chamado — ele só delega. A governança não depende de nenhum modelo "ser bonzinho" — é arquivo versionado + hooks determinísticos. A memória é externa (Qdrant), então sobrevive entre sessões.

---

## 4. O squad de agentes

Cada agente é um arquivo JSON em `agents/active/`. O orquestrador escolhe quem chamar conforme a especialidade e o tier (custo). **Squad atual:**

| Agente | Tier | Modelo | Especialidade |
|---|---|---|---|
| **Sovereign** | 4 — Architect | `anthropic/claude-sonnet-4-5` | Business Analysis & Product Documentation |
| **Shadow** | 3 — Specialist | `google/gemini-2.5-pro` | Backend & Security |
| **Chen** | 2 — Operator | `deepseek/deepseek-chat` | Backend Engineering |
| **Nova** | 2 — Operator | `google/gemini-2.5-flash` | Frontend Development |
| **Iris** | 2 — Operator | `deepseek/deepseek-v4-flash` | Frontend Development |
| **Neo** | 2 — Operator | `google/gemini-2.5-flash-lite` | Frontend Optimization |
| **Atlas** | 2 — Operator | `google/gemini-2.5-flash` | SRE & Infrastructure |
| **Lens** | 2 — Operator | `deepseek/deepseek-chat` | QA & Observability |
| **Orion** | 2 — Operator | `google/gemini-2.5-flash` | Android Development |
| **Phoenix** | 1 — Observer | `anthropic/claude-opus-4` | Elixir & Distributed Systems |
| **Falcon** | 1 — Observer | `google/gemini-2.5-flash-lite` | Documentation & Maintenance |
| **Quill** | 1 — Observer | `deepseek/deepseek-chat` | Technical Documentation |
| **Scribe** | 1 — Observer | `deepseek/deepseek-v4-flash` | Documentation & Human Handoff |

> Agentes demitidos vão para `agents/blacklist/` com um relatório de demissão (ex.: `echo.json`, demitido por alucinar em produção). O blacklist vira um **exemplo negativo rotulado** para futuras escolhas de modelo.

> **Agentes de mesma função são propositais.** Repare que há mais de um agente de frontend (Nova, Iris, Neo). Não é redundância — é experimento. Em vez de escolher um a dedo, o `duel_runner.py` os trata como um **pool competitivo** e despacha as tarefas entre eles de forma parcialmente randomizada. Cada execução gera um `DUEL_RUN` no ledger com custo, divergência e sucesso por modelo. Esses dados alimentam o `gene_crossover.py` (ADR-003), que aprende qual combinação modelo+config é mais apta — o objetivo é descobrir, por seleção, a estrutura ótima dos agentes futuros (e expor "mutações"/erros pelo caminho).

**Anatomia de um agente (JSON):**

```json
{
  "nome": "Chen",
  "tier": 2,
  "model": "deepseek/deepseek-chat",
  "specialty": "Backend Engineering",
  "evolution": "Stable",
  "success_rate": 100.0,
  "pontos": { "externos": 0, "internos": 0 },
  "tasks_completed": 0,
  "tasks_failed": 0
}
```

Esses campos não são decorativos — eles **alimentam decisões**: `evolution: Degraded` bloqueia o agente de receber tarefas; `success_rate` dispara mudanças de estado; `pontos` controlam promoção de tier.

---

## 5. Tiers e governança — por que existem

A governança evita o problema clássico de sistemas multi-agente: **agentes que erram sem consequência**. Aqui todo resultado tem efeito.

### Tiers (clearance crescente)

| Tier | Papel | Pode fazer |
|---|---|---|
| 1 — Observer | Tarefas simples, docs | Executar briefings; **não** mexe em governança |
| 2 — Operator | Engenharia de volume | Boilerplate, CRUD, componentes |
| 3 — Specialist | Decisões sensíveis | Segurança, arquitetura de risco |
| 4 — Architect | Visão de produto | Análise de negócio, documentação executiva |

Promoção exige atingir limiares de pontos (ex.: Tier 2 → 50 externos + 20 internos). **Princípio do menor privilégio:** um Observer não pode editar regras de governança nem decidir deploy.

### Pontos

- **Externos** — entregas verificáveis (código que funciona).
- **Internos** — contribuições para o squad (revisões, docs internas).

### Infrações e penalidades

| Severidade | Exemplo | Penalidade |
|---|---|---|
| Leve | Código sem comentário, typo | −1 / −1 |
| Média | Pular etapa de protocolo | −2 / −2 |
| Grave | Fabricar dado, alucinação documentada | −5 / −5 |
| Crítica | Vazar secret, destruir histórico | −10 + **Blacklist imediata** |

### Estados evolutivos

| Estado | Critério | Efeito |
|---|---|---|
| `Stable` | success_rate ≥ 85% | Operação normal |
| `Mutating` | 70–84% | Monitoramento, evitar tarefas críticas |
| `Degraded` | < 70% | **Bloqueado** de novas tarefas críticas |

> **Por que append-only?** O ledger (`project_ledger/history.json`) nunca é editado — só recebe novas entradas. Isso impede "racionalização retroativa" de decisões ruins e preserva a integridade dos cálculos de fitness.

---

## 6. As Skills

Skills são instruções especializadas que o orquestrador carrega **só quando relevante** (em `.claude/skills/`). Cada uma é uma pasta com um `SKILL.md`. Elas mantêm o prompt-base enxuto e ensinam o orquestrador a executar um processo padronizado.

| Skill | Quando ativa | O que faz |
|---|---|---|
| **agent-briefing** | "delegar", "chamar o agente", "Chen gera" | Ensina a selecionar o agente certo (tier/especialidade), montar o briefing (Contexto/Tarefa/Restrições/Entregável/Orçamento) e revisar o output |
| **deploy-committee** | "iniciar comitê de deploy" (explícito!) | Conduz o quality gate de 4 fases antes de um deploy |
| **governance-check** | classificar infração, avaliar promoção | Tabelas de penalidade, thresholds de tier, processo de blacklist |
| **ledger-log** | registrar evento no ledger | Como gravar `TASK_SUCCESS`, `INFRACTION`, `PROMOTION` etc. nos arquivos certos |
| **doc-handoff** | após integrar o output de um agente | Gera um rastro de manutenção legível (diretiva + o que/como) **dentro do projeto-alvo**, via intern barato do pool `documentation`; atualiza só a seção delimitada do README |

> A `deploy-committee` tem trava deliberada: **só ativa sob comando humano explícito**, nunca porque alguém mencionou "deploy" no meio de uma conversa.

---

## 7. Os servidores MCP

[MCP (Model Context Protocol)](https://modelcontextprotocol.io) é o "USB" das ferramentas de IA — um protocolo padrão para o orquestrador chamar ferramentas externas. O RDF expõe **dois servidores MCP**, registrados em `.mcp.json`:

### 7.1. `rubberduck-memory` (HTTP, porta 8001)

A **memória semântica** do orquestrador, sobre Qdrant. Permite lembrar decisões entre sessões sem depender do contexto da conversa.

| Tool | O que faz |
|---|---|
| `remember` | Guarda um fato/decisão como embedding vetorial |
| `recall` | Busca semântica (por significado, não por palavra exata) |
| `forget` | Remove uma memória por ID |
| `status` | Lista as memórias armazenadas |
| `cost_report` | Relatório de custo de tokens por agente/período |

> **Por que vetorial?** Você recupera uma decisão antiga mesmo sem lembrar a frase exata — a busca é por sentido. "Como decidimos lidar com auth?" encontra a nota mesmo que ela diga "estratégia de autenticação JWT".

### 7.2. `rubberduck-quality-gate` (stdio)

Ferramentas **determinísticas** para o comitê de deploy. A filosofia aqui é *"agentes raciocinam, MCP tools provam"* — nenhum veredito de deploy sai sem rodar essas ferramentas.

| Tool | O que faz |
|---|---|
| `deploy_freeze` | Ativa/desativa o Code Freeze (bloqueia Edit/Write/git) |
| `quality_gate_api_health` | Checa a saúde HTTP dos serviços Docker |
| `quality_gate_infra_read` | Lê e valida o `docker-compose.yaml` |
| `quality_gate_sast` | Análise estática de segurança (bandit) nos `.py` |
| `quality_gate_log_scan` | Varre logs recentes em busca de padrões de erro |
| `deploy_verdict` | Consolida os relatórios e emite GO / NO_GO |

Esse servidor sobe **automaticamente** quando o Claude Code abre a sessão (transporte stdio via `.mcp.json`) — não precisa subir manualmente.

---

## 8. Hooks — guardrails determinísticos

Configurados em `.claude/settings.json`, os hooks disparam por evento **antes ou depois** de cada ferramenta do Claude Code. O ponto é não depender do modelo julgar se algo é seguro — a regra é código que executa sempre.

| Hook | Evento | Ação |
|---|---|---|
| `pre_bash_guard` | antes de Bash | Bloqueia `rm -rf`, `git reset --hard`, `git push --force`, `DROP TABLE/DATABASE` |
| `pre_governance_guard` | antes de Edit/Write | Impede edição direta de `hr_policies.md` e do `blacklist/` |
| `pre_agent_schema_guard` | antes de Edit/Write | Rejeita JSON de agente com campos ausentes, tier inválido ou pontos negativos |
| `post_audit_log` | depois de Bash/Edit/Write | Registra toda operação em `hooks_audit.log` |
| `post_agent_evolution_flag` | depois de editar agente | Avisa se o `success_rate` sugere mudança de estado evolutivo |
| `session_squad_status` | início da sessão | Injeta o estado do squad no contexto inicial |
| `stop_session_digest` | fim do turno | Emite um resumo das operações do turno |

> **Por que determinístico?** Um modelo pode ser convencido (prompt injection) a fazer algo perigoso. Um hook em `pre_bash_guard` que bloqueia `rm -rf` **não negocia** — ele simplesmente retorna exit 2 e barra a operação.

---

## 9. O Deploy Committee

O diferencial de segurança do RDF: antes de qualquer deploy de produção, o orquestrador vira **Release Manager** e delega uma auditoria paralela a três especialistas. Ele fica **proibido** de analisar código diretamente nesta fase — tudo passa pelas MCP tools determinísticas.

```
1. CODE FREEZE   → deploy_freeze(action="set")   (bloqueia Edit/Write/git)
       │
2. AUDITORIA     → em paralelo:
   PARALELA         Shadow (SecOps · SAST)
                    Atlas  (SRE · infra + health)
                    Lens   (QA · health + logs)
       │
3. RELATÓRIOS    → cada um devolve severity (OK→CRÍTICA) + GO/NO_GO
       │
4. VEREDITO      → deploy_verdict(reports=[...])
       │
   ┌───┴───┐
  GO      NO_GO
   │        │
 remove   mantém freeze + sumário executivo
 freeze   para intervenção humana
```

**Regra de ouro:** qualquer achado **ALTA** ou **CRÍTICA** é NO_GO automático. O freeze só sai com aprovação unânime e sem apontamentos graves.

---

## 10. Ideias de engenharia diferenciadas

O que torna o RDF interessante além do básico de multi-agente:

1. **Governança como código** — regras, tiers e penalidades em `.governance/`, versionadas. Sem regra hardcoded em script.
2. **Ledger append-only** — cadeia auditável de causa-e-efeito que alimenta a fitness dos agentes.
3. **Cache semântico local (ChromaDB)** — antes de chamar qualquer LLM remoto, busca execuções passadas similares (distância de cosseno < 0.08). Acerto = resposta instantânea, **custo zero**.
4. **Roteamento dinâmico por complexidade** — uma tarefa trivial atribuída a um modelo caro (Gemini Pro, Opus) é automaticamente rebaixada para um modelo leve, protegendo o orçamento.
5. **Agente heurístico local (custo zero)** — tarefas como formatação (Black/Prettier), limpeza de log ou validação de sintaxe rodam localmente, sem API.
6. **Compressão LLM-DSL** — com `--dsl`, os agentes respondem num markdown mínimo (`[FILE:path] [CONTENT]...[END_CONTENT]`), cortando até 90% dos tokens de output. Um parser compila os arquivos localmente.
7. **Seleção genética (ADR-003, em avaliação)** — ao criar um novo agente, herdar as combinações modelo+ruleset de maior fitness histórico e descartar as associadas a degradação. Seleção artificial aplicada a configs de agente.
8. **Fable 5 como orquestrador sob demanda (`RDF_FABLE`)** — o modelo mais caro do stack só é acionado com o gatilho explícito `RDF_FABLE <tarefa>`, atuando como Architect Tier 4. Sem o gatilho, a delegação normal (opus/gemini) segue intacta. Detalhes no `CLAUDE.md`.

---

## 11. Como testar — passo a passo

### Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) rodando
- [Claude Code](https://claude.ai/code) instalado
- Chave da [OpenRouter](https://openrouter.ai/keys) (1 API para todos os modelos do squad)
- Python 3.12 no host (para o quality gate): `pip install bandit pyyaml mcp`

### 1. Configurar ambiente

```bash
cp .env.example .env
# Edite o .env e preencha:
#   OPENROUTER_API_KEY=sk-or-v1-...   (obrigatório — agentes do squad)
#   ANTHROPIC_API_KEY=...             (opcional — acesso direto à API)
#   GEMINI_API_KEY=...                (opcional — só se for usar Gemini direto)
```

### 2. Subir o stack

```bash
docker compose up -d
```

Serviços:
- Dashboard: http://localhost:3001
- Qdrant UI: http://localhost:6333/dashboard
- MCP memória: http://localhost:8001/mcp

> O container `orchestrator` roda um demo e **sai com exit 0** — isso é normal, não é erro.

### 3. Abrir o Claude Code no diretório

```bash
cd C:\RubberDuckFactory
claude
```

O Claude Code carrega o `.mcp.json` automaticamente e registra os dois servidores MCP. As tools `remember`/`recall`/`forget`/`status` ficam disponíveis na sessão.

### 4. Testar a delegação a um agente

```bash
uv run python agents/agent_runner.py --agent chen --task "Implementar endpoint POST /api/items com validacao. 201 em sucesso, 422 em falha."
```

Observe que ao final o JSON do agente (`agents/active/chen.json`) e o ledger (`project_ledger/history.json`) são atualizados automaticamente.

### 5. Testar o modo hello-world (todos os agentes)

```bash
uv run python agents/agent_runner.py
```

### 6. Parar o stack

```bash
docker compose down
```

---

## 12. FAQ para quem está testando

**P: Preciso de uma chave de API por modelo?**
Não. Todos os agentes do squad passam pela **OpenRouter** — uma única chave dá acesso a Gemini, DeepSeek, Claude etc.

**P: O `orchestrator` container saiu sozinho. Quebrou?**
Não. Ele roda um demo e encerra (exit 0). É o comportamento esperado.

**P: Apareceu `GEMINI_API_KEY não setada`.**
Aviso inofensivo. Só importa se você for chamar Gemini fora da OpenRouter. O stack sobe normalmente.

**P: O endpoint `:8001/mcp` retorna 406 no navegador.**
Esperado. O `/mcp` exige headers de SSE; um GET simples é recusado. O servidor está saudável.

**P: Onde vejo o histórico do que aconteceu?**
- `project_ledger/history.json` — eventos granulares de agente (append-only)
- `project_ledger/history_log.json` — marcos de projeto narrativos
- `project_ledger/hooks_audit.log` — auditoria de toda operação (gerado em runtime)

**P: Como funciona o controle de custo?**
Cada chamada registra tokens e custo no ledger (`cost_tracker.py` conhece a tarifa de cada modelo). A tool MCP `cost_report` gera um relatório por agente/período.

**P: Posso adicionar uma ferramenta nova ao orquestrador?**
Sim. Basta adicionar uma função `@mcp.tool()` ao `server.py` — sem mudanças de protocolo.

---

## Estrutura de pastas (referência rápida)

```
RubberDuckFactory/
├── .claude/
│   ├── settings.json          # Configuração dos hooks (guardrails)
│   ├── hooks/                 # Scripts Pre/Post/Session/Stop
│   └── skills/                # agent-briefing · deploy-committee · governance-check · ledger-log
├── .governance/
│   ├── hr_policies.md         # Tiers, pontos, infrações, demissão
│   └── model_caution_list.md  # Modelos a evitar e por quê
├── agents/
│   ├── active/                # 12 agentes ativos (JSON)
│   ├── blacklist/             # Agentes demitidos + causa
│   └── agent_runner.py        # Runner de delegação (OpenRouter)
├── board/                     # Dashboard Next.js (:3001)
├── docs/                      # ADRs (decisões de arquitetura)
├── project_ledger/            # history.json (append-only) + auditoria
├── .mcp.json                  # Registro dos 2 servidores MCP
├── server.py                  # MCP de memória (FastMCP + Qdrant)
├── quality_gate_server.py     # MCP do quality gate (deploy)
├── cost_tracker.py            # Cálculo de custo por modelo
├── docker-compose.yaml        # Stack completo
├── CLAUDE.md                  # Regras de orquestração + delegação
└── GUIA.md                    # Este documento
```

---

*Para a referência rápida (comandos, stack, tabelas), veja o `README.md`. Para as regras de orquestração que o Claude segue, veja o `CLAUDE.md`.*
