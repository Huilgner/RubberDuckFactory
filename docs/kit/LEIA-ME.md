# Kit de governança — feature nº 1 do RDF

> Extraído do laboratório SIGO_Fenix (2026-08), onde nasceu e foi provado em
> produto real. Contexto e tese: `../blueprints/RubberDuckFactory/blueprint_R01.md §2.1`.

## O que é

Quatro peças que dão lastro a um projeto sem matar a velocidade:

| Peça | Onde vive | Papel |
|---|---|---|
| `CLAUDE.md` do projeto | raiz do projeto | Regras de sessão — carrega sozinho em toda conversa aberta na pasta |
| Blueprint(s) | `docs/blueprints/<PROJETO>/` (aqui no RDF) | Fonte da verdade: regras, decisões, pendências coladas à regra que as originou |
| `RETOMAR.md` | raiz do projeto | Prompt de retomada datado — por onde começar e o que ler antes |
| `PENDENCIAS.md` | raiz do projeto | Diário de bordo — aponta para a blueprint, nunca a substitui |

## Como aplicar a um projeto

1. Copie `TEMPLATE_CLAUDE_PROJETO.md` → `<projeto>\CLAUDE.md` e preencha os
   `<campos>`.
2. Copie `TEMPLATE_RETOMAR.md` → `<projeto>\RETOMAR.md` e preencha o estado
   **real e datado** (rode os comandos de verificação antes de escrever).
3. Crie `<projeto>\PENDENCIAS.md` vazio com o cabeçalho do template (está
   dentro do TEMPLATE_CLAUDE_PROJETO).
4. O blueprint continua morando aqui no RDF (`docs/blueprints/<PROJETO>/`).
   Se o projeto ainda não tem um, a primeira sessão faz a arqueologia e emite
   o R00.

## Política de tokens — a regra de ouro

**Aponte, não cole.** O prompt aponta caminho e seção; a sessão lê só o que
foi apontado. Nunca colar blueprint inteira numa conversa.

**Dose por ação.** Um debug precisa de menos contexto que um deploy. Quem
monta o prompt (o launcher, ou você) escolhe a carga — não existe "carregar
tudo por via das dúvidas".

Custo de referência (medido no SIGO): abertura de sessão ≈ 5–8k tokens de
input — centavos; com cache, menos.

## Quando criar um `BP_IDX.md`

**Só com ≥ 3 blueprints no projeto.** Com um ou dois documentos, a estrutura
de § do próprio blueprint roteia sozinha — um índice seria burocracia.
Referência de forma: `../blueprints/SIGO_FENIX/BP_IDX.md` (roteamento por
tema, nomes `BP_<TEMA><nº legado>`, número nunca muda porque o código o
referencia).

## O que o kit NÃO é

- Não é o squad de agentes (isso é P&D da plataforma — `BP_DEC01.md D3`).
- Não é obrigatório para laboratório vibe (Vis.Uau fica sem, de propósito —
  `BP_DEC01.md D5`).
- Não é retroativo: projeto dormente só recebe o kit quando for tocado.
