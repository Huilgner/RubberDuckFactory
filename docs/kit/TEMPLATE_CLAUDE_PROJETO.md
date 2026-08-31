<!--
TEMPLATE do kit RDF — copie para <projeto>\CLAUDE.md e preencha os <campos>.
Apague os comentários <!-- --> ao preencher. Fonte: SIGO_Fenix (provado em
produto real). Não adicione seções por precaução — cada linha aqui é lida em
TODA sessão do projeto e custa contexto.
-->

# <PROJETO> — instruções de sessão

Projeto em `<CAMINHO, ex.: C:\MeuProjeto>`. O produto é
`<dir/stack principal, ex.: frontend/ — React + tRPC + drizzle/MySQL>`.
<Uma linha sobre o que está deprecated ou fora do produto, se houver.>

Português do Brasil, sempre.

## Fluxo de trabalho

**Este projeto trabalha por tarefa, não por tema.** Uma sessão termina quando a
tarefa está resolvida — não quando ela cruza a fronteira de outro assunto.

Se um debug de tela revelar que a regra de negócio está errada, a sessão muda a
regra. Se a correção exigir mexer no schema, a sessão mexe no schema. Nada
disso é "assunto de outra conversa".

O prompt de abertura (`RETOMAR.md`) escolhe **por onde começar** e o que ler
antes. Ele não é cerca: uma vez dentro da tarefa, siga até o fim.

O que vale em qualquer caso:

- **Nada de destrutivo sem perguntar.** Liste o que existe antes de apagar.
- **Não invente regra de negócio.** Se não está decidido, devolva `null`/erro
  e pergunte.
- **Valide contra dado real**, não só teste sintético.

## Quando a sessão termina

Quando a tarefa termina — implementada, com o que ela quebrou corrigido,
testada e registrada. Intenção nova, dias depois, é tarefa nova em sessão
nova: não reaproveite a conversa anterior pela familiaridade com o arquivo.

## Antes de passo irreversível: olhe, não lembre

Deploy, migração, remoção de campo. Leia o estado atual — `git status`,
`git diff`, o schema — antes de agir; o que era verdade no começo da sessão
pode ter sido esta própria sessão que mudou. Deploy sai de árvore limpa, a
partir de commit ou tag nomeado — nunca de "o que estiver no disco".

## Antes de investigar: leia a fonte da verdade

**A fonte da verdade não está neste repositório.** Está em
`C:\RubberDuckFactory\docs\blueprints\<PROJETO>\`.

Antes de investigar qualquer tema, abra
<`o BP_IDX.md` se o projeto tiver ≥ 3 blueprints | `o blueprint_Rnn.md de
maior versão` caso contrário> e leia **só a seção que trata do assunto**.

Não cole blueprint inteira na conversa. Aponte, não cole.

## Ao terminar: registre o que mudou

Ao final de qualquer trecho de trabalho relevante, acrescente uma entrada
curta em `PENDENCIAS.md`, na raiz do projeto:

- **o que mudou** — uma ou duas linhas, sem repetir a regra;
- **qual blueprint foi tocado** — e se ele ainda descreve a realidade;
- **o que ficou pendente** — e onde a pendência mora.

O `PENDENCIAS.md` é diário de bordo: aponta para a blueprint, não a
substitui. Regra de negócio mora só na blueprint — duplicar cria duas versões
para divergirem.

<!-- Cabeçalho para criar o PENDENCIAS.md do projeto:

# <PROJETO> — log de pendências

> Diário de bordo, em ordem cronológica inversa (mais recente no topo).
> Uma entrada por trecho de trabalho relevante. Curta — **o que mudou**,
> **qual blueprint foi tocado**, **o que ficou pendente**.
> Ao passar de dez entradas, as mais velhas migram para
> `PENDENCIAS-ARQUIVO.md`. Este arquivo é leitura de abertura, não acervo.

---
-->

## RubberDuckFactory é exceção ao isolamento

`C:\RubberDuckFactory\` **não é um projeto vizinho.** É o hub de método,
agentes e blueprints compartilhados — as blueprints deste projeto moram lá.
Acesso a ele é esperado e não deve ser bloqueado.

## Isolamento de projetos vizinhos

Este projeto **não lê, não referencia e não reaproveita código** de outras
pastas de projeto da máquina (<listar vizinhas, ex.: C:\SIGO_FENIX\,
C:\visuau\, ...>). Código de lá não é referência para cá, mesmo que resolva
problema parecido — vale para leitura, busca (`grep`/`glob`) e cópia.

**Se precisar de ferramenta ou referência existente, procure primeiro nos
blueprints do RubberDuckFactory.** Se não houver, diga que não há e proponha
escrever no projeto.
