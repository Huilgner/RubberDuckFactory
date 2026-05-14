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
- Infractions: Leve (−5), Média (−15), Grave (−30 + warning), Crítica (dismissal)
- Dismissal moves agent JSON to `agents/blacklist/` with a dismissal report
- Ledger of all actions in `history.json` — append-only, never edit past entries

---

## Running the Stack

```bash
# Start all services
cd C:\RubberDuckFactory
docker compose up -d

# Services:
# board (Next.js UI)  → http://localhost:3001
# qdrant (vector DB)  → http://localhost:6333
# mcp-server          → http://localhost:8001/mcp
# orchestrator        → runs demo and exits (exit 0 is normal)
```

The MCP server must be running for `remember`/`recall`/`forget`/`status` tools to work.

---

## Model Caution List

See `.governance/model_caution_list.md` before assigning a model to a new agent.
Key prohibitions: models < 30B params for code, `*-thinking/*-r1` variants for simple tasks, Gemini 1.5 family (discontinued on OpenRouter), any model ID without `provider/` prefix.

---

## Gene Selection (ADR-003)

Idea documented in `docs/ADR-003-selecao-artificial-configuracoes-agente.md` — status: Em avaliação.
Do not implement without explicit approval. Mentions of "gene pool" or "fitness selection" refer to this ADR.
