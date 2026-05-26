# Skill: Ledger Log

## Quando usar

Ative esta skill sempre que precisar **registrar um evento no ledger**:
task concluída, falha, alucinação detectada, infração aplicada, promoção de tier, blacklist, ou marco de projeto.

---

## Dois Arquivos, Dois Propósitos

| Arquivo | Formato | Uso |
|---|---|---|
| `project_ledger/history.json` | `{ "logs": [...] }` | Eventos granulares de agente — cada ação, outcome, penalidade |
| `project_ledger/history_log.json` | Array raiz `[...]` | Milestones descritivos com contexto narrativo |

**Regra:** ações de agente → `history.json`. Marcos de projeto → `history_log.json`. Eventos relevantes vão nos dois.

**Regra absoluta:** append-only. Nunca editar ou remover entradas passadas.

---

## Tipos de Evento — history.json

| type | Quando | Campos obrigatórios |
|---|---|---|
| `TASK_SUCCESS` | Agente completou corretamente | `timestamp, type, agent, task` |
| `TASK_FAILURE` | Agente falhou sem alucinação | `timestamp, type, agent, task, reason` |
| `HALLUCINATION` | Agente fabricou dados/respostas | `timestamp, type, agent, task, description` |
| `INFRACTION` | Penalidade aplicada | `timestamp, type, agent, severity, description, penalty_ext, penalty_int` |
| `PROMOTION` | Agente subiu de tier | `timestamp, type, agent, from_tier, to_tier, reason` |
| `BLACKLIST` | Agente removido do squad | `timestamp, type, agent, reason, final_points_ext, final_points_int` |
| `HUMAN_PROMPT` | Prompt recebido do PO | `timestamp, type, prompt` |

---

## Como Adicionar em history.json

Leia o arquivo → adicione o novo objeto ao array `logs[]` → grave de volta.

Timestamp sempre em ISO 8601 UTC com Z:
- Python: `datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")`
- JS: `new Date().toISOString()`

---

## Como Adicionar em history_log.json

Leia o arquivo → adicione novo objeto ao array raiz → grave de volta.

IDs seguem o padrão `PRJ-NNN`. Verifique o último ID registrado e incremente.
Campo `resultado` padrão: `"Sucesso"`.

---

## Templates

Use os arquivos em `templates/` como base para cada tipo de evento.
Substitua todos os campos entre `[ ]` antes de gravar.
