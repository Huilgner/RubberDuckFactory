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
