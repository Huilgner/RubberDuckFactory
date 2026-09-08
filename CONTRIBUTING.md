# RubberDuckFactory — o que é, o que faz, e como entrar

Documento de entrada do repositório. A tese completa está em
`docs/blueprints/RubberDuckFactory/blueprint_R01.md`; as regras de sessão, em
`docs/AI_CHARTER.md`. Aqui é o mapa e o passo a passo.

---

## 1. O que é

O RDF é **o meio-termo entre o desenvolvimento "real" e o vibe coding**:
velocidade de vibe coding para quem tem noção de regras, segurança, deploy e QA
— "como dar a um sênior uma equipe para seus projetos".

Não serve o vibe coder puro (que não sente falta de lastro) nem o cético
absoluto (que não quer IA no fluxo). Serve quem quer a agilidade **sem abrir mão
de revisão, rastro de decisão e capacidade de dizer não**.

O produto tem quatro componentes:

| Componente | O que é |
|---|---|
| **Kit de governança** (`docs/kit/`) | Templates que dão lastro a um projeto: `CLAUDE.md`, `RETOMAR.md`, `PENDENCIAS.md` + blueprint |
| **Launcher** (`launcher/index.html`) | HTML estático que monta o prompt de abertura já com a política de contexto embutida. Zero token, zero servidor |
| **Governança agnóstica** (`docs/AI_CHARTER.md` + `tools/gen_adapters.py`) | Um núcleo, adaptadores gerados por ferramenta, enforcement no git |
| **Squad** (`agents/`) | 13 agentes especialistas via OpenRouter, com teto de orçamento. Opcional |

---

## 2. O que ele consegue fazer

Cada item abaixo foi verificado em uso, não é promessa de roadmap.

- **Sobreviver à troca de ferramenta.** As regras vivem em `docs/AI_CHARTER.md`.
  Os arquivos que cada IDE carrega (`CLAUDE.md`, `.clinerules`, `.cursorrules`,
  `AGENTS.md`) são **gerados** e descartáveis. Ferramenta descontinuada = uma
  linha a menos no `rdf.manifest.json`.
- **Impedir que a governança apodreça em silêncio.** `hooks/pre-commit` bloqueia
  o commit se um adaptador foi editado à mão. Vale para qualquer ferramenta,
  porque todas commitam por git.
- **Carregar contexto barato.** A regra é *aponte, não cole*: o prompt aponta
  arquivo e seção, a sessão lê só aquilo. Abertura de sessão ≈ 5–8k tokens de
  input (medido no laboratório SIGO).
- **Manter continuidade entre sessões e entre ferramentas.** `RETOMAR.md` e
  `FACTORY_HANDOFF.md` guardam o estado no repositório, com data e comando de
  verificação. A ferramenta escolhe o formato.
- **Delegar trabalho de volume.** `agents/agent_runner.py` despacha para o menor
  tier que resolve, com teto de custo em `.governance/budget.json` que bloqueia
  de verdade ($5/dia, $50/mês).
- **Rodar um gate de deploy.** `quality_gate_server.py` expõe SAST, health de
  API, leitura de infra e um veredito Go/No-Go acoplado a code freeze.
- **Diagnosticar a própria instalação.** `python rdf_doctor.py`.

---

## 3. O que ele NÃO consegue fazer

Esta seção é tão importante quanto a anterior. Ler antes de confiar.

- **Não impede comando destrutivo em ferramenta sem API de hook.** Os guards de
  runtime (`rm -rf`, `git reset --hard`, `DROP TABLE`) vivem em
  `.claude/hooks/` e **só funcionam no Claude Code**. Numa sessão de Antigravity,
  Cline ou Cursor a única rede é o `pre-commit` — que age no commit, não antes
  do comando. Nenhum desenho dentro do repositório resolve isso.
- **Markdown não obriga ninguém.** Charter, playbooks e kit funcionam por
  cooperação: toda ferramenta lê, nenhuma é obrigada a obedecer. Só git e CI são
  binding. Regra que decorre: **o que é caro se violado tem que ser um check,
  não um parágrafo.**
- **Não é multiusuário.** As blueprints vivem num repositório git próprio em
  `docs/blueprints/`, **local e sem remoto**. O ledger e o squad ativo também
  são locais por desenho. Nada disso viaja num clone.
- **Não roda fora do Windows sem ajuste.** Quatro hooks têm
  `C:\RubberDuckFactory` chumbado (`post_audit_log`, `pre_code_freeze`,
  `session_squad_status`, `stop_session_digest`) e o launcher carrega caminhos
  `C:\` inline no array `PRODUTOS`.
- **O launcher está incompleto.** Faltam RifaRegional, ColheitaDeLaranjas e o
  próprio RDF no seletor; dois caminhos estão marcados `⚠ confirme` no código; e
  não há telemetria — o critério de avanço v0→v1 ("usado em ≥ 5 sessões sem
  editar o prompt na mão") não tem como ser medido.
- **O squad é stateless.** O agente não vê a conversa, nem a blueprint, nem os
  hooks. Tudo que ele precisa saber tem que estar no briefing.
- **Módulos congelados desde 2026-08-25.** Duelos, `gene_crossover`,
  Wilson/fitness, `doc-handoff` e **escrita no `project_ledger/`** continuam no
  git mas fora do protocolo. Não reative sem atender o critério em
  `BP_DEC01.md`. Em 3 meses foram 50 tarefas e US$ 0,46 — sem variância não há
  fitness a selecionar.
- **`mcp` está preso ao 1.x.** O 2.x renomeou `FastMCP` para `MCPServer` e
  quebra `server.py` e `quality_gate_server.py`. O teto `<2` é intencional.

---

## 4. Primeiros passos

```bash
git clone <repo> && cd RubberDuckFactory

# 1. OBRIGATÓRIO — o git não propaga isto no clone.
#    Sem este comando você não tem nenhum guardrail.
git config core.hooksPath hooks

# 2. Dependências (Python 3.12)
uv sync                       # ou: pip install -e . && pip install pytest

# 3. Segredos
cp .env.example .env          # preencha OPENROUTER_API_KEY

# 4. Confirme a instalação
python rdf_doctor.py          # avisos de Docker são esperados sem os serviços
python -m pytest tests -q     # 32 testes
python tools/gen_adapters.py --check

# 5. Opcional — serviços
docker compose up -d          # board :3001 · qdrant :6333 · mcp-server :8001
```

Depois disso, abra a sessão pelo `launcher/index.html`: escolha o produto e a
ação, descreva o que quer, copie o prompt.

---

## 5. Como trabalhar aqui

- **Apresente o diff antes de escrever** no código-fonte ou no banco. Vale para
  output de agente e para o seu próprio.
- **Nunca sem aprovação explícita:** apagar governança, blueprint ou histórico;
  `rm -rf`, `git reset --hard`, `git push --force`, `DROP TABLE`; delegar decisão
  arquitetural, JSON de agente, `.governance/` ou operação git.
- **Tipos antes da lógica** (ADR-005): modele o domínio, passe pelo gate de
  revisão dos tipos, só então escreva a lógica.
- **Ao encerrar**, deixe o estado no repositório: `RETOMAR.md` ou
  `FACTORY_HANDOFF.md`, mais o `PENDENCIAS.md`. Plano que só existe dentro da
  IDE some junto com ela.
- **Decisão vigente não se re-litiga** sem atender um critério de revisita.
  Estão em `BP_DEC01.md` e `BP_DEC02.md`.

### Nunca edite à mão

| Arquivo | Por quê |
|---|---|
| `CLAUDE.md`, `.clinerules`, `.cursorrules`, `AGENTS.md` | Gerados. Edite `docs/AI_CHARTER.md` e rode `python tools/gen_adapters.py`. Já editou o adaptador? `--promote <arquivo>` sobe a mudança em vez de perdê-la |
| `agents/active/*.json` | Fenótipo local (stats de cada usuário). O genoma versionado é `agents/pool/`; use `agents/sync_pool.py` |

### Nunca versione

Blueprints, `project_ledger/`, `agents/active/`, `sites/`, `.env` e os projetos
em si. São dados privados de cada usuário, não código da plataforma — já estão
no `.gitignore`, e o job `leak-guard` do CI barra num PR.

---

## 6. Mapa do repositório

```
docs/AI_CHARTER.md          núcleo de governança (bloco PISO = inegociável)
docs/kit/                   templates de projeto
docs/playbooks/             procedimentos (2 dos 5 estão congelados — ver §5 do charter)
docs/blueprints/            git próprio, local, não versionado aqui
rdf.manifest.json           índice de máquina: adaptadores, paths protegidos
tools/gen_adapters.py       gera os arquivos de instrução das IDEs
hooks/pre-commit            guardrail que vale para qualquer ferramenta
.claude/hooks/              guardrails de runtime — só Claude Code
agents/pool/                genoma do squad (versionado)
agents/active/              fenótipo local (ignorado)
launcher/index.html         montador de prompt, estático
quality_gate_server.py      MCP do comitê de deploy
rdf_doctor.py               diagnóstico da instalação
```

---

## 7. Onde pedir contexto

| Pergunta | Arquivo |
|---|---|
| "Por que o RDF existe?" | `blueprint_R01.md §1` |
| "Por que esta decisão é assim?" | `BP_DEC01.md`, `BP_DEC02.md` |
| "Como abro uma sessão?" | `launcher/index.html` |
| "Como aplico o kit a um projeto novo?" | `docs/kit/LEIA-ME.md` |
| "O que está pendente?" | `blueprint_R01.md §6` e `§7` |
| "Onde paramos?" | `RETOMAR.md` ou `FACTORY_HANDOFF.md` — o mais recente |
