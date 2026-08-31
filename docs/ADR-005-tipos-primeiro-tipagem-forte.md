# ADR-005 — Tipos-Primeiro e Preferência por Tipagem Forte

**Status:** Fase 1 IMPLEMENTADA (2026-08-01, a pedido do Arquiteto): carta de engenharia
do squad (`SQUAD_CODING_CHARTER` em `agents/agent_runner.py`) anexada a todo system prompt,
e protocolo de decomposição "tipos-primeiro" no Sovereign (`ruleset SOV-002`). Fase 2 (hook
determinístico que bloqueia tarefa de lógica sem tipos revisados) segue proposta.
**Data:** 2026-08-01
**Autor:** Opus 4.8 (orquestrador sob demanda), a pedido do Arquiteto.

---

## Contexto

O Arquiteto observou, ao inspecionar código em linguagens fortemente tipadas, maior
eficiência e menor taxa de retrabalho. Até aqui o squad não tinha **nenhuma** política de
linguagem ou de ordem de construção: nenhuma persona (`agents/active/`, `agents/pool/`),
nem o `CLAUDE.md`, nem o `.clinerules` mencionavam tipagem, clean code ou modelagem de
domínio. Os agentes escolhiam stack e ordem de implementação livremente, e a lógica de
negócio frequentemente era escrita antes de os contratos de dados existirem.

## Decisão

Adotar duas regras, em camadas distintas para evitar redundância:

### Regra A — Preferência por tipagem forte (camada de execução)

Uma **carta de engenharia única** (`SQUAD_CODING_CHARTER`) é anexada por
`build_system_prompt()` a **todos** os agentes de execução — tanto os que têm
`system_prompt` override quanto os gerados por campo. Um só ponto de verdade, versionado,
que cobre agentes futuros automaticamente. A carta exige, ao produzir código:

- **Tipagem forte:** preferir o modo mais tipado de cada stack (TypeScript sobre JS puro,
  Python com type hints + checagem estática, Rust, Go, Kotlin, Java, C#, Elixir com `@spec`).
- **Tipos antes da lógica**, **clean code** e **documentação** de toda API/tipo público.

O Sovereign **não** passa por `build_system_prompt` (é servido por `sovereign_runner.py`
lendo o JSON direto), por isso a Regra B vive na persona dele.

### Regra B — Ordem tipos-primeiro (camada de orquestração)

O `system_prompt` do Sovereign ganhou o **PROTOCOLO DE DECOMPOSIÇÃO — TIPOS PRIMEIRO**,
que torna inviolável a sequência de tarefas de qualquer feature com novos contratos:

1. **T-001 — Modelagem de Domínio:** define todas as interfaces/structs/classes/tipos, sem
   lógica. Delegada a agente de stack fortemente tipada.
2. **Gate de revisão dos tipos** (Arquiteto ou revisão interna Shadow/Lens) antes de liberar
   implementação.
3. **T-002+ — Lógica de negócio:** dependem de T-001 (via seção *Dependências* que o Briefing
   já possui) e implementam contra os tipos aprovados, sem redefini-los.

O `.clinerules` §5 recebeu a mesma diretriz para o orquestrador interativo.

## Consequência

- Contratos de dados revisados antes de qualquer lógica → menos retrabalho e menos
  divergência de tipos entre tarefas paralelas.
- Sem duplicação: a preferência de linguagem mora em **um** ponto de código; a ordem de
  construção mora na **única** persona que decompõe tarefas.
- Encaixa no formato de Briefing existente (Tarefas + Dependências), sem novo maquinário.
- **Limitação (por isso Fase 2):** as regras são impostas por prompt, não por hook. Um agente
  que desobedeça ainda pode pular a etapa. A Fase 2 propõe um hook (estilo `pre_code_freeze`)
  que bloqueia uma entrega de lógica se o artefato de tipos correspondente não existir/foi
  revisado — mesmo padrão de endurecimento gradual do ADR-004.

## Arquivos tocados

- `agents/agent_runner.py` — constante `SQUAD_CODING_CHARTER` + append em `build_system_prompt`.
- `agents/pool/sovereign.json` e `agents/active/sovereign.json` — protocolo tipos-primeiro,
  `ruleset_version SOV-001 → SOV-002` (via `sync_pool.py --update`, stats preservadas).
- `.clinerules` §5 — diretriz de delegação tipos-primeiro.
