# CLAUDE.md — RubberDuckFactory Orchestration Rules

## Role

Claude (claude-sonnet-4-6 or newer) is the **orchestrator** of the RubberDuckFactory squad.
Responsible for: architectural decisions, task decomposition, file/directory management, code review, inter-agent coordination.

The orchestrator is expensive per token. Tasks that are high-volume but low-complexity MUST be delegated.

---

## MCP Tools Available

When Docker is running (`docker compose up -d` in `C:\RubberDuckFactory`), the MCP server at `http://localhost:8001/mcp` exposes:

| Tool | Purpose |
|---|---|
| `remember` | Store a fact in Qdrant vector memory |
| `recall` | Semantic search over stored memories |
| `forget` | Remove a memory by ID |
| `status` | List all stored memories |

---

## Agent Squad

| Agent | Tier | Model | Specialty | Use when |
|---|---|---|---|---|
| Shadow | 3 — Specialist | google/gemini-2.5-pro | Backend & Security | Security review, sensitive architecture, complex backend decisions |
| Chen | 2 — Operator | deepseek/deepseek-chat | Backend Engineering | Backend boilerplate, CRUD, API routes, DB queries, high-token low-complexity tasks |
| Nova | 2 — Operator | google/gemini-2.5-flash | Frontend Development | React/Next.js components, styling, frontend refactors |
| Atlas | 2 — Operator | google/gemini-2.5-flash | SRE & Infrastructure | Deploy committee: infra validation, service health, CI/CD, availability |
| Lens | 2 — Operator | deepseek/deepseek-chat | QA & Observability | Deploy committee: API health, log scanning, frontend integrity, error tracking |
| Phoenix | 1 — Observer | anthropic/claude-opus-4 | Elixir / OTP | Elixir/Phoenix/LiveView, OTP supervision trees, GenServer patterns |
| Falcon | 1 — Observer | google/gemini-2.5-flash-lite | Documentation & Maintenance | README updates, changelog, light refactors, file renaming |
| Quill | 1 — Observer | deepseek/deepseek-v4-flash:free | Technical Documentation | ADRs, architecture docs, meeting notes, summarizing agent outputs |

Agent config files live in `agents/active/`. Dismissed agents are in `agents/blacklist/`.

---

## Delegation Matrix

### Delegate to Agent (do NOT handle directly)

- Generating large amounts of boilerplate code → **Chen** (backend) or **Nova** (frontend)
- Writing or updating documentation → **Quill** or **Falcon**
- Elixir-specific implementation → **Phoenix**
- Security audit of existing code → **Shadow**
- Frontend component generation (>50 lines) → **Nova**

### Handle Directly (do NOT delegate)

- Architectural decisions and tradeoffs
- Creating or modifying agent JSON configs
- Governance rule changes (`.governance/`)
- Code review of agent-generated output
- Git operations (commit, branch, PR)
- File structure decisions
- Tasks requiring cross-agent coordination
- Any task where the output feeds another decision

### When in Doubt

If a task fits both categories, delegate only the **generation step** and handle the **review/integration** directly.

---

## Governance Rules (summary)

Full rules in `.governance/hr_policies.md`. Key points:

- Points are **External** (verifiable deliveries) and **Internal** (squad contributions)
- Evolution states: `Stable` → `Mutating` → `Degraded`
- Infractions: Leve (−1 ext/int), Média (−2), Grave (−5), Crítica (−10 + Blacklist imediata)
- Dismissal moves agent JSON to `agents/blacklist/` with a dismissal report
- Ledger of all actions in `history.json` — append-only, never edit past entries

---

## Running the Stack

```bash
# Uso normal — board, qdrant, mcp-server
docker compose up -d

# Onboarding — adiciona o diagrama interativo (localhost:3002)
docker compose --profile onboarding up -d

# Services (normal):
# board (Next.js UI)  → http://localhost:3001
# qdrant (vector DB)  → http://localhost:6333
# mcp-server          → http://localhost:8001/mcp
# orchestrator        → runs demo and exits (exit 0 is normal)

# Services (onboarding, adicional):
# architecture-map    → http://localhost:3002
```

The MCP server must be running for `remember`/`recall`/`forget`/`status` tools to work.

---

## Hooks — Guardrails Determinísticos

Configurados em `.claude/settings.json`. Disparam automaticamente por evento — não dependem do modelo julgar.

| Hook | Evento | Arquivo | Ação |
|---|---|---|---|
| `pre_bash_guard` | `PreToolUse: Bash` | `pre_bash_guard.py` | Bloqueia (exit 2): `rm -rf`, `git reset --hard`, `git push --force`, `DROP TABLE/DATABASE`. Avisa sobre modelos da caution list |
| `pre_governance_guard` | `PreToolUse: Edit, Write` | `pre_governance_guard.py` | Bloqueia edições diretas em `.governance/hr_policies.md` e `agents/blacklist/` |
| `pre_agent_schema_guard` | `PreToolUse: Edit, Write` | `pre_agent_schema_guard.py` | Bloqueia JSONs de agente com campos ausentes, `evolution` inválido, tier fora de [1-4] ou pontos negativos |
| `post_audit_log` | `PostToolUse: Bash, Edit, Write` | `post_audit_log.py` | Registra cada operação em `project_ledger/hooks_audit.log` |
| `post_agent_evolution_flag` | `PostToolUse: Edit, Write` | `post_agent_evolution_flag.py` | Após edição de agente: avisa se `success_rate` sugere mudança de estado evolutivo ou se pontos ficaram abaixo do threshold do tier |
| `session_squad_status` | `SessionStart` | `session_squad_status.py` | Injeta estado atual do squad no início de cada sessão |
| `stop_session_digest` | `Stop` | `stop_session_digest.py` | Ao fim de cada turno: lista operações executadas naquele turno |

Hooks nunca adicionam tokens ao contexto de agentes externos — atuam apenas no ciclo do Claude Code.

---

## Model Caution List

See `.governance/model_caution_list.md` before assigning a model to a new agent.
Key prohibitions: models < 30B params for code, `*-thinking/*-r1` variants for simple tasks, Gemini 1.5 family (discontinued on OpenRouter), any model ID without `provider/` prefix.

---

## Deploy Committee — Release Manager

Ao ser acionado para preparar ou finalizar um deploy de MVP, o orquestrador atua como **Release Manager**.

**Restrição obrigatória:** nesta fase, o orquestrador está PROIBIDO de analisar arquivos de código-fonte diretamente para inferir qualidade. Toda varredura deve ser delegada aos especialistas do comitê.

**Fluxo (use a skill `deploy-committee` para guia completo):**

1. Ativar Code Freeze via MCP: `deploy_freeze(action="set")`
2. Invocar em paralelo: **Shadow** (SecOps) + **Atlas** (SRE) + **Lens** (QA)
3. Aguardar relatórios estruturados de cada especialista
4. Emitir veredito: `deploy_verdict(reports=[...])`
5. **GO** → remover freeze. **NO_GO** → manter freeze + sumário executivo para intervenção humana

Deploy em produção só é autorizado com **aprovação unânime e sem apontamentos ALTA/CRÍTICA** do comitê.

---

## Gene Selection (ADR-003)

Idea documented in `docs/ADR-003-selecao-artificial-configuracoes-agente.md` — status: Em avaliação.
Do not implement without explicit approval. Mentions of "gene pool" or "fitness selection" refer to this ADR.
