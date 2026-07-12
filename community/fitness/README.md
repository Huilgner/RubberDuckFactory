# community/fitness — Fitness Agregado do Squad Global

Cada usuário do RDF pode contribuir com um resumo **agregado e anônimo** do
desempenho dos modelos no seu squad local:

```bash
python agents/export_fitness.py --user seu_nome
# revise o output (só contagens/taxas/custo por modelo e ruleset) e abra um PR
```

**O que entra:** taxas de sucesso, contagens de tarefas/duelos, tokens e custo,
agregados por modelo e por ruleset.

**O que NUNCA entra:** texto de tarefas, nomes de projetos, respostas de agentes,
caminhos de arquivos, blueprints, logs. A allowlist está em
`agents/export_fitness.py` (`SAFE_EVENT_TYPES`).

Esses dados alimentam a seleção artificial do ADR-003 (`gene_crossover.py`) com
variância de fitness de **todos** os squads — a evolução acelera sem que os dados
de projeto de ninguém saiam da própria máquina.
