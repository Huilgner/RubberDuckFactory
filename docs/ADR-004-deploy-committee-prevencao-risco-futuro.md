# ADR-004 — Deploy Committee v2: Prevenção de Risco Futuro

**Status:** Fase 1 IMPLEMENTADA (2026-07-11, aprovada pelo Arquiteto): veredito persistido
(`DEPLOY_VERDICT` no ledger), freeze acoplado ao GO (`unset` exige veredito GO posterior;
`override` exige justificativa auditada via `FREEZE_OVERRIDE`), e ≥3 achados MÉDIA = NO_GO.
Fases 2–3 (evidência no veredito, gate de testes, blast radius, pós-deploy) seguem propostas.
**Data:** 2026-07-11
**Autor:** Fable 5 (orquestrador sob demanda), a pedido do Arquiteto.

---

## Contexto

O Deploy Committee atual (`quality_gate_server.py`) é um **snapshot do presente**: SAST,
saúde dos serviços, validação do compose e scan de logs no momento do gate. Ele responde
"o sistema está saudável AGORA?", mas o objetivo declarado do Arquiteto é outro:

> "Evitar que o RDF permita deploys que no futuro causem mais problemas do que vantagens."

Um deploy pode passar em todos os gates atuais e ainda assim ser um mau negócio:
migração de banco irreversível, mudança sem rollback, funcionalidade que quebra em produção
horas depois, ou padrão de deploys apressados que o histórico já mostrou dar errado.

### Lacunas identificadas no comitê atual

| # | Lacuna | Risco |
|---|---|---|
| L1 | `deploy_verdict(reports=[...])` **confia em severidades autodeclaradas** — nada prova que os agentes rodaram as tools | Agente (ou usuário apressado) declara "OK" e o gate aprova sem evidência |
| L2 | O veredito **não é persistido** no ledger — `deploy_verdict` retorna o dict e ele se perde | Sem memória de deploys: impossível aprender com falhas passadas |
| L3 | `deploy_freeze(action="unset")` **remove o freeze sem exigir GO** | Qualquer sessão destrava o código sem passar pelo comitê |
| L4 | Nenhum gate **executa testes/build** do projeto | Código que nem compila pode receber GO |
| L5 | Nenhuma avaliação de **reversibilidade e raio de explosão** | Migrações irreversíveis e deleções de dados passam com a mesma régua de um ajuste de CSS |
| L6 | O processo **termina no GO** — não há observação pós-deploy | Falha 10 minutos depois do deploy não gera NO_GO retroativo nem rollback |
| L7 | Agregação de severidade fraca: 10 achados MÉDIA ainda dão GO | Dívida acumulada passa despercebida |
| L8 | Override humano de NO_GO não é auditado | Decisões de exceção somem sem causa registrada |

---

## Decisão proposta

### 1. Veredito baseado em evidência, não em declaração (L1)

`deploy_verdict` passa a exigir, por relatório, o **payload bruto da tool** que sustenta a
severidade (`evidence: {tool, raw_result, executed_at}`). O servidor valida:

- `executed_at` dentro da janela do freeze atual;
- severidade declarada **coerente** com o resultado bruto (recalculada pelas mesmas regras
  determinísticas de `SEVERITY_RANK`) — divergência → NO_GO automático por tentativa de
  burla, evento `GATE_FRAUD` no ledger e infração **Grave (−5)** para o agente.

Alternativa mais simples (fase 1): `deploy_verdict` **re-executa** internamente as quatro
tools determinísticas e usa os relatórios dos agentes apenas como interpretação/contexto.

### 2. Ledger de deploys + memória de reincidência (L2)

Todo veredito vira evento `DEPLOY_VERDICT` no histórico (via `ledger_io.append_history`),
com projeto, blockers, relatórios e resultado. Antes de emitir novo veredito, o comitê
consulta os últimos N deploys do projeto:

- último deploy do projeto terminou em `POST_DEPLOY_FAILURE` → régua sobe um nível
  (MÉDIA passa a bloquear) até um deploy limpo;
- ≥2 overrides humanos recentes no mesmo projeto → exigir relatório de Reversibilidade
  (item 4) obrigatório.

É o mesmo princípio da blacklist de agentes, aplicado a deploys: **reincidência
documentada aumenta a pressão do gate**.

### 3. Freeze acoplado ao veredito (L3)

`deploy_freeze(action="unset")` só executa se existir um `DEPLOY_VERDICT` GO **posterior**
ao `set` atual (token do veredito gravado no `.code_freeze`). Destravar sem GO exige
`action="override"` com campo `reason` obrigatório → evento `FREEZE_OVERRIDE` no ledger (L8).

### 4. Novo relatório: Reversibilidade & Raio de Explosão (L5) — o coração do pedido

Quarta dimensão do comitê, respondida pelo **Release Manager (orquestrador)** com apoio de
uma tool determinística `quality_gate_blast_radius()` que inspeciona o diff congelado:

| Sinal detectado no diff | Classificação |
|---|---|
| Migração de schema / `ALTER\|DROP\|DELETE` em SQL | **Irreversível** → exige backup verificado + plano de rollback escrito |
| Mudança em autenticação, secrets, portas expostas | **Alto raio** → Shadow revisa obrigatoriamente |
| Mudança em arquivos com muitos dependentes (via `file_registry.json`) | **Alto acoplamento** → exige gate de testes verde |
| Só assets/docs/estilo | **Baixo risco** → fluxo normal |

Regra de decisão: **deploy irreversível sem plano de rollback documentado = NO_GO
automático**, independentemente das outras severidades. É isso que impede o "mais
problemas do que vantagens": o custo futuro de desfazer passa a ser um critério de gate.

### 5. Gate de testes/build determinístico (L4)

Nova tool `quality_gate_tests()`: roda a suíte do projeto (pytest / `npm run build` /
`tsc --noEmit`, conforme manifesto do projeto no blueprint). Sem suíte → severidade mínima
MÉDIA ("projeto sem rede de proteção") — nunca OK. Falha de teste → ALTA (NO_GO).

### 6. Fase 5: Observação pós-deploy com rollback (L6)

O GO deixa de encerrar o processo:

1. Deploy executado → evento `DEPLOY_EXECUTED`;
2. `self_healing_deploy.py` (já existente) entra em modo sentinela: re-executa
   `api_health` + `log_scan` em T+5min e T+30min;
3. Regressão de saúde → evento `POST_DEPLOY_FAILURE` + acionamento do plano de rollback
   registrado na fase 4 + freeze reativado automaticamente.

Isso fecha o ciclo: o comitê passa a ter dados reais de "deploy que passou no gate mas
falhou depois" — exatamente o sinal que falta hoje para calibrar as réguas (e alimenta
o item 2).

### 7. Agregação de severidade (L7)

No `deploy_verdict`: **≥3 achados MÉDIA** em qualquer combinação de relatórios → NO_GO
(dívida acumulada), destravável apenas por override auditado (item 3).

---

## Ordem de implementação sugerida

| Fase | Itens | Esforço | Valor |
|---|---|---|---|
| 1 | 2 (ledger de deploys) + 3 (freeze acoplado) + 7 (agregação) | Baixo — só `quality_gate_server.py` | Fecha as burlas mais fáceis |
| 2 | 5 (gate de testes) + 1 (evidência no veredito) | Médio | Gate passa a provar, não confiar |
| 3 | 4 (blast radius) + 6 (pós-deploy/rollback) | Alto | Cumpre o objetivo central do ADR |

## Consequências

- **Positivas:** deploys irreversíveis sem rollback ficam impossíveis de aprovar; vereditos
  viram dados auditáveis que retroalimentam a régua; burlar o comitê passa a custar pontos.
- **Negativas:** mais atrito por deploy (aceitável para produção; MVPs internos podem usar
  perfil reduzido `--profile mvp` só com fases 1–2); `quality_gate_blast_radius` exige
  heurísticas sobre diffs que precisarão de calibração.

## Referências

- `quality_gate_server.py` — implementação atual do gate
- `agents/self_healing_deploy.py` — base para a fase 5
- `ledger_io.py` — escrita segura no histórico (pré-requisito, já implementado)
- ADR-003 — precedente do princípio "pressão evolutiva guiada por histórico"
