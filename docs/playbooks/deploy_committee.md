# Skill: Deploy Committee

## Quando usar

> [!CAUTION]
> **APENAS ative esta skill sob comando explícito e direto do usuário humano** solicitando o início formal do comitê de deploy ou a execução de gates de release (ex: "iniciar comitê de deploy", "rodar quality gate de release", "executar release").
> 
> **NÃO ative esta skill de forma automática ou prematura** apenas porque o usuário ou o agente mencionou palavras isoladas como "deploy", "produção", "release" ou "freeze" no meio do desenvolvimento de features, debates arquiteturais ou correções. Ela destina-se estritamente à fase de auditoria pré-release.

Palavras-chave restritas para ativação explícita: "iniciar comitê de deploy", "rodar comitê de liberação", "executar comitê de deploy", "iniciar quality gate".

---

## Princípio fundamental

**Agentes raciocinam. MCP tools provam.**
Nenhum especialista emite veredito sem antes executar as ferramentas determinísticas correspondentes.
O orquestrador não lê código-fonte diretamente nesta fase — consolida relatórios e emite o veredito final.

---

## Workflow de 4 Fases

### Fase 1 — Code Freeze
```
deploy_freeze(action="set")
```
Ativa o freeze. O hook `pre_code_freeze` bloqueia automaticamente Edit/Write/git commit enquanto o flag `.code_freeze` existir.

### Fase 2 — Delegação Assíncrona
Invocar os 3 especialistas **em paralelo**:

| Agente | Papel | Escopo | MCP Tools |
|---|---|---|---|
| **Shadow** | SecOps | DB, Auth, Security, RLS, Rate Limiting | `quality_gate_sast` |
| **Atlas** | SRE | Infra, CI/CD, Availability | `quality_gate_infra_read`, `quality_gate_api_health` |
| **Lens** | QA | Frontend, API, Logs | `quality_gate_api_health`, `quality_gate_log_scan` |

### Fase 3 — Consolidação
Cada especialista retorna um relatório estruturado com:
- `severity`: OK | LEVE | MÉDIA | ALTA | CRÍTICA
- `scope`: domínio auditado
- `findings`: achados das MCP tools
- `recommendation`: GO | NO_GO

### Fase 4 — Veredito
```
deploy_verdict(reports=[
  {"agent": "Shadow", "scope": "SecOps", "severity": "<valor>"},
  {"agent": "Atlas",  "scope": "SRE",    "severity": "<valor>"},
  {"agent": "Lens",   "scope": "QA",     "severity": "<valor>"},
], project="<nome do projeto>")
```

O veredito é **persistido automaticamente** no ledger como `DEPLOY_VERDICT` (ADR-004).

**GO** → deploy autorizado, remover freeze: `deploy_freeze(action="unset")`
> O `unset` **só funciona** se existir um veredito GO emitido DEPOIS do freeze atual —
> destravar sem comitê exige `deploy_freeze(action="override", reason="<justificativa>")`,
> que grava `FREEZE_OVERRIDE` auditado no ledger.

**NO_GO** → deploy abortado, freeze mantido, gerar sumário executivo para intervenção humana

---

## Regras de Bloqueio (ADR-004 fase 1)

| Severidade | Ação |
|---|---|
| OK / LEVE | Deploy autorizado com registro |
| MÉDIA | Registrar no ledger; **3+ achados MÉDIA no total = NO_GO automático** (dívida acumulada) |
| ALTA | **NO_GO automático** — intervenção obrigatória |
| CRÍTICA | **NO_GO automático** — intervenção obrigatória + registro de incidente |

---

## Em caso de NO_GO

1. Manter o Code Freeze ativo
2. Gerar sumário executivo identificando o agente bloqueador e o achado
3. Registrar evento no ledger (`TASK_FAILURE` com reason = sumário)
4. Aguardar intervenção humana
5. Após correção: re-executar o quality gate completo (Fases 2-4) antes de autorizar deploy

---

## Ferramentas MCP disponíveis (rubberduck-quality-gate)

| Tool | O que faz |
|---|---|
| `deploy_freeze` | Ativa/desativa/consulta o Code Freeze |
| `quality_gate_api_health` | Verifica saúde HTTP dos serviços Docker |
| `quality_gate_infra_read` | Lê e valida docker-compose.yaml |
| `quality_gate_sast` | Análise estática de segurança (bandit) nos arquivos Python |
| `quality_gate_log_scan` | Escaneia logs recentes em busca de padrões de erro |
| `deploy_verdict` | Consolida relatórios e emite GO / NO-GO |
