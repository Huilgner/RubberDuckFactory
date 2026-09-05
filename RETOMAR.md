# RubberDuckFactory — prompt de retomada (2026-09-04)

Cole o bloco abaixo numa conversa nova, **aberta em `C:\RubberDuckFactory`**,
em qualquer ferramenta (Claude Code, Antigravity, Cline, Cursor).

> Formato irmão: `FACTORY_HANDOFF.md` — nota de passagem em prosa, escrita ao
> encerrar a sessão. Os dois convivem e a ferramenta escolhe qual usar
> (`BP_DEC02 D4`); **o mais recente é o corrente**, o outro é histórico.

---

Estou trabalhando no **RubberDuckFactory**, que **é o produto**: o meio-termo
entre o desenvolvimento "real" e o vibe coding. Esta sessão é **P&D da
plataforma** — evoluir o próprio RDF, não um projeto-filho.

**Leia antes de mexer** — abra só a seção que trata do assunto, não o
documento inteiro:

- `docs/AI_CHARTER.md` — núcleo de governança. O `§4` tem as camadas de
  guardrail; o `§5`, o status de cada playbook.
- `docs/blueprints/RubberDuckFactory/blueprint_R01.md` — a tese. `§4` roadmap
  estagiado, `§6` estado de implementação, `§7` pendências e colheita.
- `docs/blueprints/RubberDuckFactory/BP_DEC01.md` e `BP_DEC02.md` — decisões
  vigentes. **Não re-litigar sem atender um critério de revisita.**

## Estado — 2026-09-04

> Este bloco envelhece. Confirme com `git status`, `git log --oneline -5` e
> `python -m pytest tests -q` antes de confiar nele.

- **Testes**: 28 no total. **Um é flaky** (`test_quality_gate.py::
  test_go_after_freeze_unlocks`): alterna passa/falha porque
  `quality_gate_server.py` grava estado em caminhos reais do repo
  (`.code_freeze`, `project_ledger/last_verdict.json`) e o `conftest.py` não
  os redireciona para `tmp_path`. Já identificado, não corrigido.
- **Branch/tag**: `main` foi fast-forwardada hoje de `f36eaa8` (14/05) para
  `a77b150` (30/08) — `feat/agent-duel-system` era superconjunto estrito.
  **`origin/main` ainda está em `f36eaa8`: nada foi enviado.**
- **Trabalho não commitado**: a governança agnóstica desta sessão —
  `rdf.manifest.json`, `tools/gen_adapters.py`, `hooks/pre-commit`,
  `docs/AI_CHARTER.md` reescrito, `docs/playbooks/`, `BP_DEC02.md`, e os 4
  adaptadores gerados (`CLAUDE.md`, `.clinerules`, `.cursorrules`, `AGENTS.md`).
- **Rede de segurança**: `stash@{0}` (04/09 10:25) guarda o refactor original
  do Antigravity antes das correções. Não descartar sem conferir.
- **Squad**: 13 agentes em `agents/active/`, reconstruídos do `agents/pool/`
  via `python agents/sync_pool.py --bootstrap`.
- **Docker**: desligado. `board`, `qdrant` e `mcp-server` inacessíveis — o
  `rdf_doctor` acusa 3 avisos, e o MCP `rubberduck-memory` não conecta.

## Ambiente

```bash
docker compose up -d          # board :3001 · qdrant :6333 · mcp-server :8001/mcp
python -m pytest tests -q     # suíte
python rdf_doctor.py          # diagnóstico da instalação
python tools/gen_adapters.py  # regera os adaptadores de IDE
python tools/gen_adapters.py --check   # o mesmo check que o pre-commit roda
```

**Clone novo precisa de** `git config core.hooksPath hooks` — o git não
propaga essa configuração no clone, por design.

## Como trabalho

O geral está no adaptador que sua ferramenta carregou sozinha (o bloco PISO).
Específico desta conversa:

- **Não edite `CLAUDE.md`, `.clinerules`, `.cursorrules` ou `AGENTS.md`** — são
  gerados. Edite `docs/AI_CHARTER.md` e rode `--sync`; se já editou o adaptador,
  use `--promote <arquivo>`. O pre-commit bloqueia o commit se divergirem.
- Estado de sessão vai para **o repositório** — este arquivo ou o
  `FACTORY_HANDOFF.md`, o que a sua ferramenta usar — e para o `PENDENCIAS.md`.
  Nunca só para dentro da IDE (`BP_DEC02 D4`). Date, e diga qual ferramenta e
  modelo produziram o estado.
- Decisões de projetos-filhos (SIGO, CastleVote, Vis.Uau) estão em segundo
  plano por decisão do CTO em 04/09. O foco é a plataforma.

## Próximo passo

1. **Usar o RDF por uma semana nas duas ferramentas** e verificar se o
   `pre-commit` dispara sozinho. É o marco declarado em `BP_DEC02` antes de
   portar os guards de estado de `.claude/hooks/` para o `pre-commit`.
2. Fechar o ciclo da colheita (`R01 §7`): o `launcher` já pergunta ao fim das
   sessões do Vis.Uau o que fez falta, mas ninguém grava a resposta.
3. Consertar o teste flaky (item 1 do Estado).

> **Já foi feito — não refaça:** o merge da `feat/agent-duel-system` na `main`;
> o bootstrap do squad; a correção do `server.py` (o refactor do Antigravity
> tinha revertido `cost_report`, cache semântico e `setup_api_routes`); e a
> reescrita do `AI_CHARTER.md` — a primeira versão dele havia perdido a tese do
> R01, a seção de congelados e o gate de revisão de código-fonte.

> **Pendência de segurança, fora do escopo desta sessão:** o remote em
> `.git/config` carrega um PAT do GitHub em texto plano. Revogar e trocar por
> credential helper.
