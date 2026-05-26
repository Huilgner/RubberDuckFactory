# Skill: Deploy Committee

## Quando usar

Ative esta skill ao preparar um deploy, release ou quality gate de MVP.
Palavras-chave: "deploy", "release", "produção", "quality gate", "code freeze", "go/no-go", "comitê de revisão".

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
])
```

**GO** → deploy autorizado, remover freeze: `deploy_freeze(action="unset")`
**NO_GO** → deploy abortado, freeze mantido, gerar sumário executivo para intervenção humana

---

## Regras de Bloqueio

| Severidade | Ação |
|---|---|
| OK / LEVE | Deploy autorizado com registro |
| MÉDIA | Registrar no ledger, deploy pode prosseguir com aprovação explícita |
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
