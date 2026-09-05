# Skill: Doc Handoff — Trilho de Manutenção Humana

## Quando usar

Ative **automaticamente logo após integrar o output de um agente do squad num projeto-alvo** (código aplicado, arquivos escritos/editados). O objetivo é deixar **dentro do próprio projeto** um rastro legível para um mantenedor **humano** — o que o orquestrador pediu, o que foi feito e como — de forma que ele consiga manter o código **sem depender do RDF**.

**NÃO ative** para: tarefas que não alteraram o projeto-alvo; modo hello-world; ou para a própria geração desta doc (anti-recursão — ver Regras).

---

## Princípio: fatos são mecânicos, prosa é barata

A entrada de manutenção mistura dois tipos de conteúdo, tratados de formas diferentes:

- **Esqueleto factual** (diretiva, agente, modelo, tier, arquivos, timestamp, resultado) → você monta direto dos dados da tarefa. São **fatos conhecidos** — nunca invente, nunca peça a um modelo para "lembrar".
- **Prosa** (o que foi feito / como / nota ao mantenedor) → gerada por um **intern barato** do pool `documentation`, **ancorada no diff real**. O intern resume o que está no código, não supõe.

Isso mantém o custo em centavos e blinda os fatos contra alucinação.

---

## Fluxo

### 1. Reúna os fatos da tarefa recém-integrada
- **Diretiva** — o `--task` que o orquestrador deu ao agente
- **Executor** — nome do agente + modelo + tier
- **Arquivos afetados** — caminhos **no projeto-alvo**
- **Timestamp** — UTC, ISO 8601
- **Resultado** — sucesso / falha

### 2. Gere a prosa com um intern barato (grounded no diff)
```bash
uv run python agents/duel_runner.py --role documentation --task "<PROMPT_PROSA>"
```
O `<PROMPT_PROSA>` deve **incluir o diff/conteúdo real dos arquivos alterados** e pedir exatamente três blocos curtos:
1. **O que foi feito** (1–3 frases)
2. **Como / decisões** (escolhas técnicas relevantes ao mantenedor)
3. **Nota ao mantenedor** (onde olhar, gotchas, o que NÃO mexer)

Instrução obrigatória no prompt: *"Resuma SOMENTE o que o diff mostra. Não descreva comportamento que não está no código. Se algo não estiver claro no diff, diga 'não evidente no diff'."*

> O pool `documentation` (Quill, Falcon — modelos baratos) é selecionado por sorteio ponderado e ainda alimenta o ADR-003. Nunca use o orquestrador para escrever a prosa longa.

### 3. Componha a entrada
Use `templates/maintenance_entry.md`, substituindo todos os campos `{{...}}`.

### 4. Coloque no projeto-alvo (você, orquestrador)
- **Log:** faça **append** da entrada em `<projeto>/docs/AI_MAINTENANCE_LOG.md` (crie o arquivo/pasta se não existir). **Append-only** — nunca edite ou remova entradas passadas.
- **README:** atualize **somente** o conteúdo entre os marcadores `<!-- AI:START -->` e `<!-- AI:END -->`. Se os marcadores não existirem, **adicione-os ao final** do README sem tocar em mais nada. **Nunca** edite fora dos marcadores.

---

## Regras

- **Append-only no log** — é histórico; só cresce.
- **README só entre os marcadores** — conteúdo escrito por humanos é intocável.
- **Anti-recursão** — gerar esta doc **não** é uma nova "tarefa de agente"; não re-dispare o handoff a partir dela.
- **Grounded** — a prosa descreve apenas o que o diff mostra; sem suposições sobre o que não foi alterado.
- **Custo** — sempre via pool `documentation` (modelos baratos). O orquestrador monta só o esqueleto factual (barato) e coloca os arquivos.

---

## Por que no projeto, e não no RDF?

O `project_ledger/history.json` do RDF é **auditoria de máquina** (governança, fitness, ADR-003). Este log é para o **humano** que vai manter o código: vive no projeto-alvo, é legível, e continua útil mesmo que o RDF nunca seja aberto. São dois propósitos distintos — não os misture.
