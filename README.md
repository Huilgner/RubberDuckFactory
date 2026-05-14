
<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />

# RubberDuckFactory

**A multi-agent governance system for AI-assisted software development.**

Claude orchestrates a squad of specialized LLM agents, each governed by a tier system, a points ledger, and evolutionary fitness rules. The factory delegates: expensive cognition stays with the orchestrator, high-token low-complexity work goes to cheaper agents.

</div>

---

## Table of Contents

- [Stack](#stack)
- [How to Use](#how-to-use)
- [Agent Squad](#agent-squad)
- [Engineering Ideas](#engineering-ideas)
- [Logical Principles](#logical-principles)
- [Governance Rules](#governance-rules)
- [Project Structure](#project-structure)

---

## Stack

| Service | Technology | Port | Role |
|---|---|---|---|
| `board` | Next.js 15 (App Router, standalone Docker) | `3001` | Project dashboard UI |
| `qdrant` | Qdrant vector database | `6333` | Agent semantic memory |
| `mcp-server` | Python + FastMCP + uvicorn (HTTP transport) | `8001` | MCP tool server (remember/recall/forget) |
| `orchestrator` | TypeScript + tsx (Node 20 Alpine) | — | Demo runner, exits after execution |
| `Coolify` | Self-hosted PaaS via WSL | `8000` | Deployment management (separate stack) |

**LLM access:** [OpenRouter](https://openrouter.ai) — unified API gateway for all agent models.

**Orchestrator:** Claude Code (claude-sonnet-4-6+) running locally, connected to the MCP server via `.mcp.json`.

---

## How to Use

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) running
- [Claude Code](https://claude.ai/code) installed
- OpenRouter API key (set in `.env`)

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env and set OPENROUTER_API_KEY
```

### 2. Start the stack

```bash
docker compose up -d
```

Services available at:
- Dashboard: http://localhost:3001
- Qdrant UI: http://localhost:6333/dashboard
- MCP server: http://localhost:8001/mcp

### 3. Open Claude Code in this directory

```bash
cd C:\RubberDuckFactory
claude
```

Claude Code will auto-load `.mcp.json` and register the `rubberduck-memory` MCP server. The tools `remember`, `recall`, `forget`, and `status` become available in the session.

### 4. Start a session

Claude is the orchestrator. Describe what you want to build. Claude will:
- Handle architectural decisions and code review directly
- Delegate high-token boilerplate tasks to the appropriate agent (see [Agent Squad](#agent-squad))
- Store decisions in Qdrant memory for future recall
- Record all task outcomes in `project_ledger/history.json`

### 5. Running agents manually (optional)

```bash
# Requires OPENROUTER_API_KEY in environment
cd agents
python agent_runner.py --agent shadow --task "Review authentication module for security issues"
```

### Stopping the stack

```bash
docker compose down
```

---

## Agent Squad

Agents are defined as JSON files in `agents/active/`. Each has a model, tier, specialty, evolution state, and points.

| Agent | Tier | Model | Specialty | Evolution |
|---|---|---|---|---|
| **Shadow** | 3 — Specialist | `google/gemini-2.5-pro` | Backend & Security | Stable |
| **Chen** | 2 — Operator | `deepseek/deepseek-chat` | Backend Engineering | Stable |
| **Nova** | 2 — Operator | `google/gemini-2.5-flash` | Frontend Development | Mutating |
| **Phoenix** | 1 — Observer | `anthropic/claude-opus-4` | Elixir / OTP | Stable |
| **Falcon** | 1 — Observer | `google/gemini-2.5-flash-lite` | Documentation & Maintenance | Stable |
| **Quill** | 1 — Observer | `deepseek/deepseek-v4-flash:free` | Technical Documentation | Stable |

**Tiers:** `1 = Observer` → `2 = Operator` → `3 = Specialist` → `4 = Architect (reserved)`

Dismissed agents are moved to `agents/blacklist/` with a dismissal report. See `agents/blacklist/echo.json` for an example (dismissed for hallucination in production).

---

## Engineering Ideas

### 1. Governance-as-Code

Agent behavior, tiers, penalties, and promotion rules are defined in `.governance/hr_policies.md` — versioned alongside the code. No hardcoded rules in scripts: the governance file is the single source of truth.

### 2. Append-only Ledger

Every task outcome, promotion, demotion, and dismissal is recorded in `project_ledger/history.json`. The ledger is **never edited** — only appended. This creates a complete, auditable cause-and-effect chain that feeds into fitness calculations.

### 3. Cost-aware Delegation

Claude (orchestrator) is billed per token and handles complex reasoning. Agents are cheaper models suited for repetitive, high-volume tasks. The delegation matrix in `CLAUDE.md` encodes the boundary: "generate boilerplate → delegate; review output → orchestrate."

### 4. Evolutionary Fitness (ADR-003 — in evaluation)

Each agent carries an `evolution` state (`Stable`, `Mutating`, `Degraded`) derived from its performance history. The long-term goal (see `docs/ADR-003`) is a **gene pool** mechanism: when spawning a new agent, inherit the model + ruleset combinations with the highest historical fitness and discard configurations associated with degradation. Analogous to artificial selection: preserve what works, pressure out what doesn't.

### 5. Vector Memory via Qdrant

Decisions, architectural notes, and task outcomes can be stored as vector embeddings via the MCP `remember` tool and retrieved semantically via `recall`. This gives the orchestrator persistent memory across sessions without relying on conversation context alone.

### 6. MCP as Tool Interface

The Python MCP server exposes tools over HTTP (FastMCP + uvicorn, streamable-http transport). Claude Code connects via `.mcp.json`. Adding new tools to the factory requires only adding a `@mcp.tool()` function to `server.py` — no protocol changes needed.

### 7. Blacklist Pressure

Agents that cause critical infractions (e.g., hallucinating in production) are dismissed rather than silently retired. The blacklist record documents the cause, creating a labeled negative example for future model selection decisions.

---

## Logical Principles

**Separation of concerns** — Claude decides, agents execute. The orchestrator never generates large blobs of boilerplate; agents never make architectural decisions.

**Principle of least privilege** — Tier controls clearance. A Tier 1 Observer cannot modify governance files or make deployment decisions. Escalation requires explicit promotion.

**Immutability of history** — The ledger is append-only. Past events cannot be revised. This prevents retroactive rationalization of bad decisions and preserves the integrity of fitness calculations.

**Cost-proportional work allocation** — Model cost should match task complexity. Expensive models (Gemini 2.5 Pro, Claude Opus) handle tasks where their capability gap matters. Free or cheap models handle tasks where any competent model will do.

**Evolutionary pressure over manual configuration** — Rather than manually tuning agent configs, the system is designed to learn which combinations produce quality and which produce degradation. Bad configs are documented (model caution list) and eventually excluded from new agent initialization.

**Fail visibly, not silently** — Errors in agent model IDs, API keys, and tool calls surface as explicit failures with documented causes, not silent fallbacks. The ledger records them. The blacklist names them.

**Semantic recall over exact lookup** — Qdrant stores memories as embeddings. Retrieval is by meaning, not exact key. This makes past decisions recoverable even when the exact phrasing is forgotten.

---

## Governance Rules

Full rules in `.governance/hr_policies.md`. Summary:

- **Points:** External (verifiable deliveries) + Internal (squad contributions)
- **Infractions:** Leve (−5 pts) → Média (−15) → Grave (−30 + warning) → Crítica (dismissal)
- **Evolution:** `Stable` ↔ `Mutating` ↔ `Degraded` — driven by recent success rate and penalty history
- **Dismissal:** Agent JSON moved to `agents/blacklist/`, event recorded in ledger

Model selection rules (what to avoid) are in `.governance/model_caution_list.md`.

---

## Project Structure

```
RubberDuckFactory/
├── .governance/
│   ├── hr_policies.md          # Tier system, points, infractions, dismissal rules
│   └── model_caution_list.md   # Models to avoid and why
├── agents/
│   ├── active/                 # Live agent JSON configs
│   └── blacklist/              # Dismissed agents with cause
├── board/                      # Next.js dashboard (Docker multi-stage)
├── docs/
│   └── ADR-003-*.md            # Architecture Decision Records
├── orchestrator/               # TypeScript demo runner
├── project_ledger/
│   └── history.json            # Append-only event log
├── .mcp.json                   # MCP server registration for Claude Code
├── CLAUDE.md                   # Orchestration rules and delegation matrix
├── docker-compose.yaml         # Full stack definition
├── server.py                   # MCP server (FastMCP + uvicorn)
└── sovereign_proxy.py          # OpenRouter proxy for agent calls
```

