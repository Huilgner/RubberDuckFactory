# HR Policies — Projeto Cofre

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

### Blacklist
Agentes que violam protocolos críticos (vazamento de dados, ações não autorizadas, falha repetida de auditoria) são movidos para `agents/blacklist/`.
- Status imediato: **suspended**
- Reintegração requer revisão manual pelo Arquiteto e quórum de agentes Tier 3+
- Pontos são zerados no evento de blacklist; histórico é preservado em `agents/clearance_memory/`
