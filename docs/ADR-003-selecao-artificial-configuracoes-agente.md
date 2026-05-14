# ADR-003: Mecanismo de Seleção Artificial de Configurações de Agente (Gene Pool)

**Autor:** Quill | **Fonte:** Product Owner | **Data:** 2026-05-14
**Status:** Em avaliação (ideia embrionária)

---

## Contexto

O sistema de governança atual registra, por agente, os seguintes dados no ledger:

- Pontos acumulados e penalidades aplicadas
- Evolution states (`Stable`, `Mutating`, `Degraded`)
- Histórico de decisões com causa e efeito

Cada agente armazena um JSON com:

- `model` — modelo LLM utilizado
- `ruleset_version` — conjunto de regras de comportamento
- `success_rate` — taxa de sucesso em tarefas
- `evolution` — estado evolutivo atual
- `pontos` — externos (entregas verificáveis) e internos (contribuições ao squad)

Ferramentas já operacionais que podem suportar a ideia:

| Ferramenta | Papel potencial |
|---|---|
| **Qdrant** | Memória vetorial — armazenar embeddings de configurações e seus resultados |
| **pleno_rag_worker.py** | Retrieval semântico — consultar padrões históricos |
| **Ledger** (`history.json`) | Registro imutável de causa e efeito |
| **Campo `evolution`** | Sinal de fitness já presente nos JSONs dos agentes |

Atualmente, ao instanciar um novo agente, as configurações (modelo, ruleset, parâmetros) são definidas manualmente. Não há mecanismo que permita ao sistema aprender, com base no histórico, quais combinações tendem a gerar código de maior qualidade e quais estão associadas a degradação.

---

## Decisão (em avaliação)

Propõe-se a criação de um **mecanismo de seleção artificial de configurações de agente**, inspirado na seleção artificial de genes:

> *Preservar o que é bom. Evitar o que não é.*

O objetivo é, a partir do histórico de sucessos e falhas registrados no ledger, identificar padrões de configuração `(modelo + ruleset + parâmetros)` que:

- Contribuem **positivamente** para qualidade de código — alto fitness
- Contribuem **negativamente** — baixo fitness / degradação

Ao inicializar um novo agente, o sistema consultaria esse histórico e **herdaria configurações de alto fitness**, descartando combinações associadas a falhas.

O mecanismo é análogo a um crossover genético: pegar o ruleset de um agente Stable de alta reputação + o modelo que produziu menos alucinações + os parâmetros com menor taxa de penalidades, e usar isso como genoma base do novo agente.

---

## Consequências

### Positivas (esperadas)

- Melhora progressiva da qualidade média do código gerado pelo squad
- Redução de tentativas e erros repetidos em agentes novos
- Aproveitamento do histórico já registrado no ledger (dados existentes)
- Adaptação contínua conforme o ambiente de desenvolvimento evolui

### Negativas / Riscos

- **Dependência de dados consistentes** — se o ledger não registrar corretamente causa e efeito, o aprendizado será enviesado
- **Overfitting** — o sistema pode favorecer configurações que funcionaram bem no passado mas não generalizam para novos cenários
- **Complexidade adicional** — requer módulo de avaliação de fitness e mecanismo de herança
- **Custo computacional** — consultas frequentes ao Qdrant e ledger podem impactar tempo de inicialização

---

## Próximos Passos

1. **Validar viabilidade dos dados** — verificar se ledger + `evolution` permitem associar configurações a resultados de qualidade mensuráveis
2. **Definir métrica de fitness** — propor fórmula que combine `success_rate`, penalidades e pontos externos
3. **Projetar mecanismo de herança** — rascunhar como um novo agente consultaria o histórico e selecionaria configurações
4. **Esboçar integração com Qdrant** — avaliar armazenamento de embeddings de configurações para retrieval semântico
5. **Criar protótipo experimental** — versão minimalista testada com dados reais do ledger
6. **Definir estratégia anti-overfitting** — exploração aleatória ocasional para evitar estagnação evolutiva
