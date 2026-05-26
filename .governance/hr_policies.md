# HR Policies — RubberDuckFactory

## Sistema de Gamificação

### Pontos Externos
Concedidos por entregas verificáveis ao cliente ou ao sistema externo (deploys, relatórios, aprovações formais).
Incrementam o Tier do agente e desbloqueiam permissões operacionais mais amplas.

### Pontos Internos
Concedidos por contribuições internas: revisões de código, documentação, suporte a outros agentes, conformidade com protocolos.
Influenciam a reputação dentro da rede de agentes mas não alteram o Tier diretamente.

### Clearance (Nível de Acesso)
Cada agente possui um nível de Clearance que determina quais operações, dados e outros agentes pode acessar.
O Clearance sobe automaticamente quando o agente atinge limiares de Pontos Externos + Internos definidos por Tier.

| Tier | Clearance | Pontos Externos Mínimos | Pontos Internos Mínimos |
|------|-----------|-------------------------|-------------------------|
| 1    | Observer  | 0                       | 0                       |
| 2    | Operator  | 50                      | 20                      |
| 3    | Specialist| 150                     | 60                      |
| 4    | Architect | 400                     | 150                     |

### Tabela de Infrações e Penalidades

| Severidade | Descrição | Exemplos | Penalidade Pts Externos | Penalidade Pts Internos | Ação Adicional |
|------------|-----------|----------|------------------------|------------------------|----------------|
| **Leve**   | Erros de sintaxe ou falta de documentação | Código sem comentários, arquivo sem header, typo em config | -1 | -1 | Registro no log de auditoria |
| **Média**  | Desobediência técnica ou falha em ler o Ledger | Ignorar `history_log.json` antes de agir, não seguir padrão Next.js/TS, pular etapa de protocolo | -2 | -2 | Registro + alerta ao Arquiteto |
| **Grave**  | Alucinação de dados ou modificação de arquivos de governança sem permissão | Fabricar dados em produção, editar `hr_policies.md` sem aprovação do CTO | -5 | -5 | Registro + revisão obrigatória pelo Arquiteto |
| **Crítica**| Blacklist imediata | Vazamento de chaves/secrets, destruição do histórico (`history_log.json`), ação não autorizada em produção | -10 | -10 | **Blacklist imediata** + pontos zerados + movido para `agents/blacklist/` |

### Blacklist
Agentes que violam protocolos críticos (vazamento de dados, ações não autorizadas, falha repetida de auditoria) são movidos para `agents/blacklist/`.
- Status imediato: **suspended**
- Reintegração requer revisão manual pelo Arquiteto e quórum de agentes Tier 3+
- Pontos são zerados no evento de blacklist; histórico é preservado em `agents/clearance_memory/`

---

## Estados Evolutivos

Cada agente possui um estado evolutivo que reflete sua confiabilidade recente. O estado é computado automaticamente a partir do `success_rate` após cada atualização de tarefa.

| Estado    | Critério de success_rate | Implicação operacional                                           |
|-----------|--------------------------|------------------------------------------------------------------|
| `Stable`  | >= 85%                   | Aceita qualquer tarefa dentro do seu tier                        |
| `Mutating`| >= 70% e < 85%           | Tarefas de alta criticidade requerem revisão do orquestrador     |
| `Degraded`| < 70%                    | Nenhuma tarefa nova sem aprovação explícita do Arquiteto         |

### Transições de Estado

Todas as transições são **automáticas**, disparadas pelo hook `post_agent_evolution_flag` após cada edição de JSON de agente.

| Transição               | Gatilho                    | Responsável       |
|-------------------------|----------------------------|-------------------|
| `Stable → Mutating`     | success_rate cai abaixo de 85% | Hook automático |
| `Mutating → Degraded`   | success_rate cai abaixo de 70% | Hook automático |
| `Degraded → Mutating`   | success_rate sobe acima de 70% | Hook automático |
| `Mutating → Stable`     | success_rate sobe acima de 85% | Hook automático |
| Qualquer → Qualquer     | Override manual do Arquiteto   | Orquestrador    |

Toda transição de estado gera uma entrada no `project_ledger/agent_ledger.log`.

---

## Rastreamento de Tarefas

Cada JSON de agente mantém contadores brutos de tarefas. O `success_rate` é derivado desses contadores e atualizado pelo orquestrador após cada tarefa concluída.

```json
"tasks_completed": 0,
"tasks_failed":    0,
"success_rate":    100.0
```

**Fórmula:** `success_rate = tasks_completed / (tasks_completed + tasks_failed) * 100`

Caso não haja tarefas registradas (`tasks_completed + tasks_failed == 0`), `success_rate` permanece em seu valor inicial e o estado evolutivo não é alterado.

**Responsabilidade:** o orquestrador atualiza `tasks_completed` ou `tasks_failed` — conforme o resultado — e recalcula `success_rate` antes de salvar o JSON.

---

## Log de Pontos e Evolução (`agent_ledger.log`)

Todo ganho ou perda de pontos e toda transição de estado evolutivo são registrados em:

```
project_ledger/agent_ledger.log
```

O arquivo é **append-only** — nunca editar ou remover entradas.

### Formato de Entrada

Cada linha é um objeto JSON (JSONL — JSON Lines), legível como texto e parseável por máquina:

```
{"ts":"2026-05-26T10:00:00Z","type":"PONTO_GANHO","agent":"Chen","delta":{"ext":+2,"int":0},"before":{"ext":0,"int":0},"after":{"ext":2,"int":0},"project":"RubberDuckFactory","reason":"API CRUD entregue e aprovada"}
{"ts":"2026-05-26T10:05:00Z","type":"PONTO_PERDIDO","agent":"Nova","delta":{"ext":-2,"int":-2},"before":{"ext":2,"int":2},"after":{"ext":0,"int":0},"project":"RubberDuckFactory","reason":"Infração Média — componente sem tipagem TypeScript"}
{"ts":"2026-05-26T10:10:00Z","type":"EVOLUCAO","agent":"Nova","from":"Stable","to":"Mutating","success_rate":84.8,"trigger":"hook_automatico"}
```

### Tipos de Entrada

| type            | Escrito por    | Quando                                              |
|-----------------|----------------|-----------------------------------------------------|
| `PONTO_GANHO`   | Orquestrador   | Após `TASK_SUCCESS` com concessão de pontos         |
| `PONTO_PERDIDO` | Orquestrador   | Após infração com penalidade aplicada               |
| `EVOLUCAO`      | Hook           | Toda transição de estado evolutivo                  |
| `TAREFA_OK`     | Orquestrador   | Conclusão registrada sem alteração de pontos        |
| `TAREFA_FALHA`  | Orquestrador   | Falha registrada sem penalidade ainda aplicada      |

### Campos Obrigatórios por Tipo

| Campo     | PONTO_GANHO | PONTO_PERDIDO | EVOLUCAO | TAREFA_OK | TAREFA_FALHA |
|-----------|:-----------:|:-------------:|:--------:|:---------:|:------------:|
| `ts`      | ✓           | ✓             | ✓        | ✓         | ✓            |
| `type`    | ✓           | ✓             | ✓        | ✓         | ✓            |
| `agent`   | ✓           | ✓             | ✓        | ✓         | ✓            |
| `delta`   | ✓           | ✓             | —        | —         | —            |
| `before`  | ✓           | ✓             | —        | —         | —            |
| `after`   | ✓           | ✓             | —        | —         | —            |
| `project` | ✓           | ✓             | —        | ✓         | ✓            |
| `reason`  | ✓           | ✓             | —        | ✓         | ✓            |
| `from`    | —           | —             | ✓        | —         | —            |
| `to`      | —           | —             | ✓        | —         | —            |
| `success_rate` | —      | —             | ✓        | —         | —            |
| `trigger` | —           | —             | ✓        | —         | —            |
