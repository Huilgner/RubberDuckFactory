# Handoff — RubberDuckFactory

> Nota de passagem: o que acabou de ser feito e o que vem a seguir.
> Formato irmão do `RETOMAR.md` (prompt de retomada datado) — os dois convivem,
> a ferramenta escolhe qual usar (`BP_DEC02 D4`). **Havendo os dois, o mais
> recente é o corrente.**

**Sessão de 2026-09-04 · Claude Code (Opus 5)**
Sessão anterior: 2026-09-04, Antigravity — refactor agnóstico inicial.

## O que foi feito

1. **Merge da `feat/agent-duel-system` na `main`** — fast-forward puro de
   `f36eaa8` (14/05) para `a77b150` (30/08). A `main` estava 3 meses e meio
   atrasada e o kit, o launcher e o ADR-005 não existiam no working tree.
   `origin/main` **ainda não recebeu push**.

2. **Squad reconstruído** — o merge esvaziou `agents/active/` (o roster passou
   a viver em `agents/pool/`, versionado). `python agents/sync_pool.py
   --bootstrap` restaurou os 13 agentes locais.

3. **Regressão do `server.py` revertida** — o refactor anterior tinha trazido
   uma versão de maio, apagando `cost_report`, o cache semântico
   (`_get_semantic_cache` / `_set_semantic_cache`) e `setup_api_routes`.

4. **Governança agnóstica de ferramenta** — a entrega principal:
   - `docs/AI_CHARTER.md` é a fonte única. O bloco entre `<!-- PISO:INICIO -->`
     e `<!-- PISO:FIM -->` é o núcleo inegociável.
   - `rdf.manifest.json` é o índice de máquina (adaptadores, paths protegidos,
     congelados, handover).
   - `tools/gen_adapters.py` gera `CLAUDE.md`, `.clinerules`, `.cursorrules` e
     `AGENTS.md` a partir do charter. `--sync` · `--check` · `--promote`.
   - `hooks/pre-commit` (via `git config core.hooksPath hooks`) bloqueia commit
     com adaptador editado à mão. É a única camada que vale para **qualquer**
     ferramenta.
   - `BP_DEC02.md` registra a decisão e os critérios de revisita.

5. **Charter corrigido** — a primeira versão dele foi remontada a partir do
   `.clinerules` de maio e havia perdido a tese do R01, os dois modos de
   sessão, o kit, o launcher, a seção de congelados e a lista "nunca delegue".
   Também estreitara o gate de revisão de "antes de qualquer escrita no
   **código-fonte ou** no banco" para só "no banco", e declarava ambiente WSL
   num projeto que roda em Windows.

## Estado verificado

Rodado nesta sessão, não lembrado:

```bash
python tools/gen_adapters.py --check   # 4 adaptadores em dia
python -m pytest tests -q              # 28 testes
python rdf_doctor.py                   # instalação OK, 3 avisos (Docker off)
```

- **Nada commitado.** A árvore tem toda a governança nova sem commit.
- `stash@{0}` (04/09 10:25) guarda o refactor original do Antigravity intacto.
- **Um teste é flaky**: `test_quality_gate.py::test_go_after_freeze_unlocks`
  alterna passa/falha porque `quality_gate_server.py` grava estado em caminhos
  reais do repo (`.code_freeze`, `project_ledger/last_verdict.json`) e o
  `conftest.py` não os isola em `tmp_path`.

## Próximos passos

1. **Usar o RDF por uma semana nas duas ferramentas** e ver se o `pre-commit`
   dispara sozinho. É o marco declarado no `BP_DEC02` antes de portar os guards
   de estado (`pre_governance_guard`, `pre_agent_schema_guard`,
   `pre_edit_guard`, `pre_code_freeze`) de `.claude/hooks/` para o `pre-commit`.
2. Fechar o ciclo da colheita (`R01 §7`) — o launcher já pergunta ao fim das
   sessões do Vis.Uau o que fez falta, e ninguém grava a resposta.
3. Consertar o teste flaky.
4. **Segurança, fora do escopo desta sessão:** o remote em `.git/config` carrega
   um PAT do GitHub em texto plano. Revogar e trocar por credential helper.

## Para o próximo agente

Seu arquivo de instrução (`CLAUDE.md`, `.clinerules`, `.cursorrules` ou
`AGENTS.md`) já carrega o piso da governança sozinho — **e é gerado**. Nunca o
edite direto: mexa em `docs/AI_CHARTER.md` e rode `python
tools/gen_adapters.py`. Se já editou o adaptador, use `--promote <arquivo>` para
subir a mudança em vez de perdê-la; o pre-commit vai barrar antes disso virar
divergência silenciosa.

Clone novo precisa de `git config core.hooksPath hooks` — o git não propaga
essa configuração.
