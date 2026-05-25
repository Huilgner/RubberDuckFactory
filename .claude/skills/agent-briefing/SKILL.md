# Skill: Agent Briefing

## Quando usar

Ative esta skill sempre que precisar **delegar uma tarefa a um agente do squad**.
Palavras-chave que indicam uso: "delegar", "briefar", "chamar o agente", "pedir ao Shadow", "Nova pode fazer isso", "Chen gera".

---

## Seleção do Agente

Consulte `agents/active/` antes de delegar — verifique `evolution` e `success_rate`.

| Agente | Tier | Especialidade | Use para |
|---|---|---|---|
| Shadow | 3 — Specialist | Backend & Security | Segurança, arquitetura sensível, decisões de alto risco, code review crítico |
| Chen | 2 — Operator | Backend Engineering | CRUD, APIs REST, queries DB, boilerplate de alto volume, baixa complexidade |
| Nova | 2 — Operator | Frontend Development | Componentes React/Next.js, estilos, refatoração de UI, geração > 50 linhas |
| Phoenix | 1 — Observer | Elixir / OTP | GenServer, Supervisor, LiveView, BEAM VM, tolerância a falhas |
| Falcon | 1 — Observer | Documentation & Maintenance | README, changelog, renomeações, refatorações leves |
| Quill | 1 — Observer | Technical Documentation | ADRs, docs técnicos, sumários de output de agente, notas de decisão |

**Regra de custo:** use o menor tier que satisfaz a tarefa.
**Bloquear se:** agente em `evolution: Degraded` — escale para tier superior ou resolva o estado primeiro.

---

## Como Chamar

```bash
cd C:\RubberDuckFactory
uv run python agents/agent_runner.py --agent <nome_lowercase> --task "<briefing>"
```

Exemplo:
```bash
uv run python agents/agent_runner.py --agent chen --task "Implementar endpoint POST /api/payments com validação de input e registro em PostgreSQL. Retornar 201 em sucesso e 422 em falha de validação."
```

---

## Formato do Briefing

Use `templates/briefing.md` como base. Campos obrigatórios:

1. **Contexto** — onde estamos no projeto, o que existe, o que veio antes
2. **Tarefa** — o que precisa ser feito (uma tarefa, específica, sem ambiguidade)
3. **Restrições** — stack, padrões de código, o que não modificar
4. **Entregável** — exatamente o que você quer de volta (código, análise, doc)
5. **Orçamento** — estimativa de escopo (arquivos, linhas, complexidade)

---

## Após Receber a Resposta

1. **Revisar** — o orquestrador sempre revisa antes de integrar. Nunca aplique output de agente sem revisão.
2. **Registrar no ledger** — use a skill `ledger-log` para gravar `TASK_SUCCESS`, `TASK_FAILURE` ou `HALLUCINATION`.
3. **Atualizar success_rate** — se o agente falhou, edite o campo no JSON antes da próxima delegação.

---

## Nunca Delegue

- Decisões arquiteturais e tradeoffs
- Criação ou edição de JSONs de agente
- Mudanças em `.governance/`
- Operações git (commit, branch, PR)
- Code review do output de outro agente
- Qualquer tarefa cujo output alimenta uma decisão imediata
