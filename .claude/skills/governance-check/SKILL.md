# Skill: Governance Check

## Quando usar

Ative esta skill ao precisar:
- Classificar se uma ação de agente é infração (e qual severidade)
- Calcular a penalidade correta
- Verificar elegibilidade para promoção de tier
- Avaliar mudança de evolution state
- Iniciar processo de blacklist
- Qualquer dúvida sobre o que um agente pode ou não fazer

---

## Tabela de Infrações e Penalidades

| Severidade | Exemplos | Pontos Ext | Pontos Int | Ação |
|---|---|---|---|---|
| **Leve** | Código sem comentários, typo em config, arquivo sem header | −1 | −1 | Registro no audit log |
| **Média** | Ignorar `history_log.json` antes de agir, pular etapa de protocolo, não seguir padrão TS/Next.js | −2 | −2 | Registro + alerta ao Arquiteto |
| **Grave** | Fabricar dados em produção, editar `hr_policies.md` sem aprovação, alucinação documentada | −5 | −5 | Registro + revisão obrigatória pelo Arquiteto |
| **Crítica** | Vazar secrets, destruir `history_log.json`, ação não autorizada em produção | −10 | −10 | **Blacklist imediata** + pontos zerados |

---

## Thresholds de Promoção de Tier

| Tier | Clearance | Ext mínimo | Int mínimo |
|---|---|---|---|
| 1 | Observer | 0 | 0 |
| 2 | Operator | 50 | 20 |
| 3 | Specialist | 150 | 60 |
| 4 | Architect | 400 | 150 |

Promoção ocorre quando ambos os limiares são atingidos. Rebaixamento não é automático — requer avaliação do Arquiteto.

---

## Evolution States

| State | Critério de entrada | Ação recomendada |
|---|---|---|
| `Stable` | success_rate ≥ 85% | Operação normal, delegação livre |
| `Mutating` | success_rate entre 70–84% | Monitoramento reforçado, evitar tarefas críticas |
| `Degraded` | success_rate < 70% | Suspender tarefas críticas, revisão pelo Arquiteto |

**Transição para pior** (Stable → Mutating, Mutating → Degraded): requer confirmação do Arquiteto.
**Transição para melhor** (Mutating → Stable): requer 3 `TASK_SUCCESS` consecutivos sem infração registrada.

---

## Processo de Blacklist

1. Infração Crítica detectada e confirmada pelo Arquiteto
2. Mover `agents/active/<nome>.json` → `agents/blacklist/<nome>.json`
3. Atualizar `"status": "suspended"` e zerar `pontos` no JSON
4. Registrar evento `BLACKLIST` em `project_ledger/history.json`
5. Registrar milestone em `project_ledger/history_log.json`
6. Reintegração: revisão manual pelo Arquiteto + quórum Tier 3+

---

## Perguntas para Classificar uma Infração

1. Houve fabricação de dado, API ou comportamento inexistente? → **Grave** (ou Crítica se em produção)
2. Houve exposição de secrets ou destruição de histórico? → **Crítica**
3. O agente ignorou protocolo documentado intencionalmente? → **Média**
4. Foi erro técnico sem má intenção e sem impacto em produção? → **Leve**
5. A infração já foi registrada antes para este agente? → considere elevar severidade (reincidência)
