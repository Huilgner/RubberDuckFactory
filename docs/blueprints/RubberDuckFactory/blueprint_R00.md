```
================================================================================
BLUEPRINT  |  RubberDuckFactory  |  R00  |  2025-01-22
================================================================================
CLIENTE         Interno
SOVEREIGN       Sovereign / RubberDuckFactory Squad
================================================================================

## S1 VISÃO DO PRODUTO

O que é: Plataforma orquestradora de squad de agentes de IA especializados, com capacidade de evolução autônoma através de competição controlada entre configurações de agentes (modelo LLM + ruleset).

Quem usa: Equipe interna de desenvolvimento e clientes que demandam execução de tarefas técnicas complexas através do squad.

Problema que resolve: 
- Custo elevado e imprevisível de operação com LLMs de alta performance
- Ausência de mecanismo objetivo para avaliar trade-off qualidade/custo entre modelos
- Degradação silenciosa de agentes sem sistema de detecção e correção
- Falta de dados estruturados para decisões de arquitetura sobre escolha de modelos

## S2 REGRAS DE NEGÓCIO

### Gestão de Agentes
- RN-001: Cada agente possui papel único (Frontend, Backend, DevOps, etc.), modelo LLM, ruleset, success_rate e estado de evolução (Stable/Mutating/Degraded)
- RN-002: Agentes são organizados em hierarquia de 4 tiers (Tier 1: Executores, Tier 2: Especialistas, Tier 3: Coordenadores, Tier 4: Arquitetos)
- RN-003: Sovereign (Tier 4) não executa código — apenas planeja, estrutura e documenta

### Sistema de Duelos (ADR-003)
- RN-004: Para cada papel existe um Champion (configuração em produção) e um Challenger (configuração experimental)
- RN-005: Duelos ocorrem em dois modos mutuamente exclusivos por tarefa:
  - SOLO: Champion e Challenger alternam tarefas simples (baixo custo, alta frequência de teste)
  - PARALLEL: Ambos executam a mesma tarefa complexa simultaneamente (expõe divergências, detecta alucinações)
- RN-006: Modo de duelo é auto-detectado por complexidade da tarefa, com possibilidade de override manual
- RN-007: Cada execução de duelo registra: custo (via cost_tracker), tempo, resultado, e atualiza success_rate do agente
- RN-008: Duelos paralelos podem usar juiz opcional (modelo barato) para escolher vencedor quando resultados divergem
- RN-009: Histórico de duelos é persistido em agents/history.json com tipo DUEL_RUN

### Evolução de Agentes (gene_crossover)
- RN-010: Dados de duelos alimentam algoritmo de seleção artificial baseado em fitness = f(qualidade, custo)
- RN-011: Configurações de alto fitness (modelo + ruleset) são promovidas a Champion ou usadas para semear novos agentes
- RN-012: Estados de evolução refletem estabilidade: Stable (produção), Mutating (teste), Degraded (requer intervenção)

### Rastreamento de Custos
- RN-013: Toda chamada a LLM é rastreada com tokens de input/output e custo em USD
- RN-014: Custos são agregados por agente, por papel, por modelo e por projeto
- RN-015: Relatórios de custo devem permitir comparação direta entre Champion e Challenger

## S3 ESTADO DE IMPLEMENTAÇÃO

| Módulo / Funcionalidade | Estado | Observações |
|-------------------------|--------|-------------|
| Orquestrador de Squad | Concluído | Next.js board + MCP server (FastMCP) |
| Agent Runner | Concluído | Execução via OpenRouter |
| Qdrant (Memória Vetorial) | Concluído | Persistência de contexto |
| Cost Tracker | Concluído | Rastreamento por chamada e agregação |
| Sistema de Duelos (duel_runner.py) | Concluído | Modos SOLO e PARALLEL implementados |
| Roster de Duelos (duel_roster.json) | Concluído | Champion vs Challenger por papel |
| Primeiro Duelo Ativo | Concluído | Frontend: Nova (gemini-2.5-flash) vs Iris (deepseek-v4-flash) |
| History.json (DUEL_RUN) | Concluído | Persistência de resultados de duelos |
| Gene Crossover (fitness básico) | Concluído | Estrutura implementada |
| Gene Crossover (fitness ponderado por custo) | Pendente | Fórmula de fitness precisa incorporar custo normalizado |
| Dashboard de Métricas de Duelo | Pendente | Visualização de qualidade x custo por modelo |
| Auto-promoção de Challenger | Pendente | Lógica para promover Challenger a Champion automaticamente |

## S4 DECISÕES ARQUITETURAIS

### DA-001: Stack de Orquestração
Problema: Necessidade de coordenar múltiplos agentes com estados independentes e memória persistente.
Decisão: Next.js (board/UI) + FastMCP (servidor de protocolo) + Qdrant (memória vetorial) + OpenRouter (gateway multi-modelo).
Consequência: Flexibilidade para trocar modelos sem refatoração; custo de manutenção de múltiplos componentes.

### DA-002: Rastreamento de Custos como Primitiva
Problema: Impossibilidade de otimizar custos sem dados granulares por agente e por tarefa.
Decisão: cost_tracker como módulo obrigatório em toda execução de agente, com persistência em banco relacional.
Consequência: Overhead mínimo (<5ms por chamada); dados estruturados para análise de ROI.

### DA-003: Sistema de Duelos de Agentes
Problema: Ausência de método objetivo para avaliar novos modelos LLM sem risco de degradação em produção.
Decisão: Implementar competição controlada Champion vs Challenger com dois modos (SOLO para tarefas simples, PARALLEL para tarefas complexas), rastreando custo e qualidade.
Consequência: 
- Positivo: Dados empíricos para decisões de modelo; detecção precoce de degradação; redução de custo mensurável (deepseek-v4-flash é ~13x mais barato que gemini-2.5-flash no output).
- Negativo: Aumento de ~50% no custo durante fase de duelo PARALLEL; necessidade de juiz em casos de divergência.
- Mitigação: Modo SOLO para 80% das tarefas (custo incremental <10%); juiz usa modelo ultra-barato.

### DA-004: Evolução por Seleção Artificial (gene_crossover)
Problema: Configurações de agentes (modelo + ruleset) degradam ao longo do tempo sem mecanismo de melhoria contínua.
Decisão: Algoritmo de seleção artificial que cruza configurações de alto fitness (qualidade/custo) para gerar novas gerações de agentes.
Consequência: Squad auto-otimizante; risco de convergência prematura se fitness não balancear qualidade e custo adequadamente.

## S5 PRÓXIMAS ENTREGAS

| Milestone | Critério de Aceitação | Estimativa |
|-----------|----------------------|------------|
| M1: Fitness Ponderado por Custo | Fórmula `fitness = (success_rate^2) / (custo_normalizado + epsilon)` implementada em gene_crossover; testes com dados históricos de Nova vs Iris | 2 dias |
| M2: Dashboard de Métricas de Duelo | Gráfico scatter qualidade x custo por modelo; tabela de win-rate Champion vs Challenger; exportação CSV | 3 dias |
| M3: Auto-promoção de Challenger | Lógica: se Challenger vence 70% dos últimos 20 duelos E custo médio <80% do Champion, promover automaticamente | 2 dias |
| M4: Segundo Duelo Ativo | Backend: Chen (claude-3.5-sonnet) vs novo Challenger (gemini-2.0-flash-thinking-exp ou qwen-2.5-coder) | 1 dia |
| M5: Relatório Semanal de Evolução | Email automático com: economia acumulada, agentes promovidos, degradações detectadas | 2 dias |

## S6 GLOSSÁRIO

| Termo | Definição para o cliente |
|-------|--------------------------|
| Champion | Configuração de agente atualmente em produção para um papel específico |
| Challenger | Configuração experimental competindo para substituir o Champion |
| Duelo SOLO | Modo de competição onde Champion e Challenger alternam tarefas simples (baixo custo de teste) |
| Duelo PARALLEL | Modo de competição onde ambos executam a mesma tarefa complexa simultaneamente (detecta divergências) |
| Fitness | Métrica composta que balanceia qualidade (success_rate) e custo de um agente |
| Gene Crossover | Algoritmo que combina características de agentes de alto fitness para gerar novas configurações |
| Ruleset | Conjunto de instruções e restrições que definem o comportamento de um agente |
| Success Rate | Percentual de tarefas concluídas com sucesso por um agente (0.0 a 1.0) |
| Estado de Evolução | Classificação de estabilidade: Stable (produção), Mutating (teste ativo), Degraded (requer correção) |
| MCP | Model Context Protocol — padrão de comunicação entre orquestrador e agentes |
| Qdrant | Banco de dados vetorial usado para memória de longo prazo dos agentes |
| OpenRouter | Gateway que abstrai acesso a múltiplos provedores de LLM (OpenAI, Anthropic, Google, DeepSeek, etc.) |

================================================================================
## REVISÕES
| Rev  | Data       | Descrição               |
|------|------------|-------------------------|
| R00  | 2025-01-22 | Emissão inicial — Sistema de Duelos implementado, fitness ponderado pendente |
================================================================================

sovereign-signature:
  author: Sovereign
  reviewed-by: Architect (implícito — demanda interna)
  last-edited-by: Sovereign
  last-edit: 2025-01-22T14:32:00Z
  model: claude-3.7-sonnet
```

---

**OBSERVAÇÕES PARA O ARQUITETO:**

1. **Ambiguidade detectada (não crítica)**: O termo "juiz opcional" em duelos paralelos não especifica critérios de ativação. Assumido: juiz é acionado quando outputs divergem semanticamente acima de threshold (ex: similarity < 0.7). Recomendo formalizar em RN futura.

2. **Risco de escopo**: M1 (Fitness Ponderado) pode requerer experimentação com múltiplas fórmulas. Se testes empíricos indicarem necessidade de >3 iterações, sinalize para revisão de estimativa.

3. **Dependência externa**: M4 (Segundo Duelo) depende de disponibilidade de créditos/acesso aos modelos candidatos (gemini-2.0-flash-thinking-exp é experimental, qwen-2.5-coder pode ter rate limits).

4. **Sugestão de RN adicional**: Considere formalizar política de rollback — se Challenger promovido degradar success_rate >15% em 48h, reverter automaticamente para Champion anterior.