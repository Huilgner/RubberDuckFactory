<!--
TEMPLATE do kit RDF — copie para <projeto>\RETOMAR.md e preencha os <campos>.
Regras deste arquivo:
- Ele NÃO repete regra de negócio (mora na blueprint) nem o que o CLAUDE.md
  do projeto já carrega sozinho. Repetir cria duas versões para divergirem.
- O bloco de Estado é DATADO e manda se verificar — nunca deve ser acreditado
  sem rodar os comandos.
- Atualize a data do título e o Estado ao fim de cada tarefa relevante (ou
  deixe que a entrada nova do PENDENCIAS.md o corrija na sessão seguinte).
-->

# <PROJETO> — prompt de retomada (<AAAA-MM-DD>)

Cole o bloco abaixo numa conversa nova, **aberta em `<CAMINHO do projeto>`**.

---

Estou trabalhando no **<PROJETO>**, <uma linha: o que é o produto>. O produto
é `<dir/stack>`. <Uma linha do que está fora do produto, se houver.>

**Leia antes de mexer**, em `C:\RubberDuckFactory\docs\blueprints\<PROJETO>\`
— abra só a seção que trata do assunto, não o documento inteiro:

- `<blueprint_Rnn.md ou BP_XXX.md>` — <o que tem lá, em meia linha, com os §
  mais consultados>.
- <repita por blueprint relevante; se houver BP_IDX.md, mande abrir ele
  primeiro e apague esta lista>.

## Estado — <AAAA-MM-DD>

> Este bloco envelhece. Confirme com <`git status`, `git log --oneline -5`,
> comando da suíte de testes> antes de confiar nele.

- **<Testes/checagens>**: <ex.: 335 testes verdes, typecheck limpo>.
- **Branch/tag**: <branch atual, HEAD, relação com origin, último deploy/tag>.
- **Trabalho não commitado**: <o que há no working tree e por quê — ou "árvore
  limpa">.
- <Estado de banco/dados/credenciais que a sessão precisa saber>.

## Ambiente

```bash
# <como subir o ambiente: container, porta, comando de dev>
# <particularidades: portas vizinhas, credenciais efêmeras, scripts úteis>
```

## Como trabalho

O geral está no `CLAUDE.md`, que carrega sozinho. Específico desta conversa:

- <ex.: banco de dev é compartilhado comigo — nada de limpeza sem pedir>
- <ex.: validar contra as planilhas reais em <caminho> antes de dar por pronto>

## Próximo passo

1. <O passo de maior retorno agora, apontando o § da blueprint que o define.>
2. <O seguinte, se houver.>

> <Avisos de "não reabra": coisas que versões anteriores deste arquivo pediam
> e que JÁ FORAM FEITAS — nomeie-as para a sessão não refazê-las.>
