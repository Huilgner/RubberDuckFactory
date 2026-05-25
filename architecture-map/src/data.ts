import { DiagramNode } from './types';

export const SYSTEM_NODES: DiagramNode[] = [
  // Band 1 - Orchestrator
  {
    id: 'orchestrator-claude',
    title: '🧠 Claude Sonnet',
    subtitle: 'Orchestrator — architectural decisions, code review, inter-agent coordination',
    type: 'orchestrator',
    borderColor: '#4FC3F7', // Electric Blue
    fillColor: '#111A24',
    chips: [
      'L2 Skills: agent-briefing',
      'deploy-committee',
      'ledger-log',
      'governance-check'
    ],
    details: {
      description: 'Claude Code (claude-sonnet-4-6+) rodando localmente como orquestrador. Responsável por decisões arquiteturais, decomposição de tarefas, revisão de código e coordenação inter-agente. Tarefas de alto volume e baixa complexidade são delegadas a agentes via agent_runner.py → OpenRouter.',
      techStack: 'Claude Code · claude-sonnet-4-6+ · execução local (não passa pelo OpenRouter)',
      parameters: ['regras: CLAUDE.md', 'governance: .governance/hr_policies.md', 'ledger: project_ledger/history.json']
    }
  },
  // Band 2 - MCP Left
  {
    id: 'mcp-memory',
    title: '🗄️ rubberduck-memory',
    subtitle: 'HTTP · Docker · localhost:8001',
    type: 'mcp',
    borderColor: '#CE93D8', // Purple
    fillColor: '#171221',
    tools: ['remember', 'recall', 'forget', 'status'],
    details: {
      description: 'Servidor MCP de memória semântica persistente. Expõe ferramentas para armazenar e recuperar fatos, decisões arquiteturais e contexto de sessões anteriores. Roda em Docker via FastMCP + uvicorn (HTTP transport).',
      techStack: 'FastMCP + uvicorn (Python) · Docker · Qdrant como backend de vetores',
      parameters: ['host: 0.0.0.0', 'port: 8001', 'transport: streamable-http']
    }
  },
  {
    id: 'db-qdrant',
    title: '🔵 Qdrant (vector DB · localhost:6333)',
    type: 'database',
    borderColor: '#CE93D8',
    fillColor: '#0D1B2A',
    details: {
      description: 'Banco de dados vetorial local. Armazena embeddings de memórias do orquestrador, permitindo recuperação semântica via recall even quando o contexto exato da conversa foi perdido.',
      techStack: 'Qdrant Docker · REST API · porta 6333',
      parameters: ['REST port: 6333', 'storage: qdrant_storage/ (volume local)', 'UI: localhost:6333/dashboard']
    }
  },
  // Band 2 - MCP Right
  {
    id: 'mcp-quality-gate',
    title: '🔒 rubberduck-quality-gate',
    subtitle: 'stdio · host Python · quality_gate_server.py',
    type: 'mcp',
    borderColor: '#4DB6AC', // Teal
    fillColor: '#101B1E',
    tools: [
      'deploy_freeze',
      'quality_gate_sast',
      'quality_gate_infra_read',
      'quality_gate_api_health',
      'quality_gate_log_scan',
      'deploy_verdict'
    ],
    details: {
      description: 'Servidor MCP de quality gate rodando no host Windows via stdio. Executa análise estática (bandit), lê e valida o docker-compose.yaml, faz health check nos serviços Docker e escaneia logs. Emite o veredito final GO/NO_GO sem intervenção do modelo.',
      techStack: 'MCP stdio · Python 3.12 (host Windows) · quality_gate_server.py',
      parameters: ['transport: stdio', 'python: C:\\Users\\huilg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe', 'deps: bandit · pyyaml · mcp']
    }
  },
  // Band 3 - Gateway
  {
    id: 'openrouter-gateway',
    title: '🌐 OpenRouter Gateway',
    subtitle: 'unified LLM gateway',
    type: 'gateway',
    borderColor: '#B0BEC5',
    fillColor: '#1A1E24',
    details: {
      description: 'Gateway unificado para acesso a múltiplos providers de LLM (Anthropic, Google, DeepSeek). Todos os agentes do squad passam por aqui via sovereign_proxy.py + agent_runner.py. O orquestrador (Claude Code) conecta diretamente à Anthropic API, não ao OpenRouter.',
      techStack: 'OpenRouter API · sovereign_proxy.py · agent_runner.py'
    }
  },
  // Row 3 - Agent Squad
  // Tier 3
  {
    id: 'agent-shadow',
    title: '👤 Shadow',
    subtitle: 'gemini-2.5-pro · Backend & Security · SecOps ★',
    type: 'agent',
    borderColor: '#FFD54F', // Gold
    fillColor: '#201E13',
    details: {
      description: 'Tier 3 Specialist — SecOps do Deploy Committee. Responsável pela auditoria de segurança via quality_gate_sast (bandit). Revisa código Python em busca de vulnerabilidades, injeções e credenciais expostas. Seu veredito de severidade ALTA ou CRÍTICA bloqueia o deploy automaticamente.',
      techStack: 'google/gemini-2.5-pro via OpenRouter',
      governanceRule: 'Tier 3 Specialist — Infração Crítica implica blacklist imediata. Único agente com clearance para revisar mudanças no quality-gate.'
    }
  },
  // Tier 2
  {
    id: 'agent-chen',
    title: '👤 Chen',
    subtitle: 'deepseek-chat · Backend Eng',
    type: 'agent',
    borderColor: '#81C784', // Green
    fillColor: '#132015',
    details: {
      description: 'Tier 2 Operator — Backend Engineering. Especializado em boilerplate de alta escala: CRUD, rotas de API, queries de banco. Modelo custo-eficiente para tarefas repetitivas de alto volume de tokens.',
      techStack: 'deepseek/deepseek-chat via OpenRouter',
      governanceRule: 'Tier 2 Operator — threshold: 50 pts externos / 20 pts internos para promoção.'
    }
  },
  {
    id: 'agent-nova',
    title: '👤 Nova',
    subtitle: 'gemini-2.5-flash · Frontend Dev',
    type: 'agent',
    borderColor: '#81C784', // Green
    fillColor: '#132015',
    details: {
      description: 'Tier 2 Operator — Frontend Development. Gera componentes React/Next.js, estilização Tailwind, refatorações de UI. Delegada para blocos de código frontend acima de 50 linhas.',
      techStack: 'google/gemini-2.5-flash via OpenRouter',
      governanceRule: 'Tier 2 Operator — Restaurada de Mutating para Stable em 2026-05-22.'
    }
  },
  {
    id: 'agent-atlas',
    title: '👤 Atlas',
    subtitle: 'gemini-2.5-flash · SRE & Infra',
    type: 'agent',
    borderColor: '#81C784', // Green
    fillColor: '#132015',
    details: {
      description: 'Tier 2 Operator — SRE do Deploy Committee. Executa quality_gate_infra_read (valida docker-compose.yaml) e quality_gate_api_health (verifica saúde HTTP dos serviços). Checa healthchecks, restart policies e disponibilidade de serviços.',
      techStack: 'google/gemini-2.5-flash via OpenRouter',
      governanceRule: 'Tier 2 Operator — Membro do Deploy Committee. Escopo: hosting, CI/CD, disponibilidade.'
    }
  },
  {
    id: 'agent-lens',
    title: '👤 Lens',
    subtitle: 'deepseek-chat · QA & Observability',
    type: 'agent',
    borderColor: '#81C784', // Green
    fillColor: '#132015',
    details: {
      description: 'Tier 2 Operator — QA do Deploy Committee. Executa quality_gate_api_health e quality_gate_log_scan. Escaneia hooks_audit.log e history.json em busca de padrões CRITICAL/ERROR/WARNING antes de autorizar deploy.',
      techStack: 'deepseek/deepseek-chat via OpenRouter',
      governanceRule: 'Tier 2 Operator — Membro do Deploy Committee. Escopo: integridade de frontend, API health, rastreamento de erros.'
    }
  },
  // Tier 1
  {
    id: 'agent-phoenix',
    title: '👤 Phoenix',
    subtitle: 'claude-opus-4 · Elixir/OTP Specialist',
    type: 'agent',
    borderColor: '#B0BEC5', // Grey
    fillColor: '#1C1E20',
    details: {
      description: 'Tier 1 Observer — Especialista em Elixir/OTP. Consultado para implementações Phoenix/LiveView, GenServer patterns e supervision trees. Modelo mais caro do squad — acionado apenas quando a expertise em Elixir é crítica.',
      techStack: 'anthropic/claude-opus-4 via OpenRouter'
    }
  },
  {
    id: 'agent-falcon',
    title: '👤 Falcon',
    subtitle: 'gemini-flash-lite · Documentation Writer',
    type: 'agent',
    borderColor: '#B0BEC5',
    fillColor: '#1C1E20',
    details: {
      description: 'Maintains codebase README layouts, system API documentation tables, and architectural journals.',
      techStack: 'Google Gemini 2.5 Flash Lite'
    }
  },
  {
    id: 'agent-quill',
    title: '👤 Quill',
    subtitle: 'deepseek-free · Tech Docs Advisor',
    type: 'agent',
    borderColor: '#B0BEC5',
    fillColor: '#1C1E20',
    details: {
      description: 'Aggregates tool parameters from workspace scripts to build structural schema maps for human operators.',
      techStack: 'DeepSeek Coder Free Tier'
    }
  },
  // Blacklist
  {
    id: 'blacklist-echo',
    title: '🚫 agents/blacklist/ — Echo',
    subtitle: 'dismissed: hallucination in production',
    type: 'blacklist',
    borderColor: '#EF9A9A', // Soft Red
    fillColor: '#241315',
    details: {
      description: 'Echo foi demitido por alucinação em produção — invocou endpoints inexistentes e gerou outputs incorretos que quebraram o pipeline. JSON movido para agents/blacklist/ com relatório de demissão. Serve como exemplo negativo para seleção de modelos futuros.',
      governanceRule: 'BLACKLIST — Infração Crítica (−10 pts + blacklist imediata). Arquivo em agents/blacklist/echo.json com causa documentada.'
    }
  },

  // Band 4 - Deploy Committee steps
  {
    id: 'step-freeze',
    title: '[Step 1: Code Freeze]',
    subtitle: 'deploy_freeze(action="set")',
    type: 'step',
    borderColor: '#FF9800', // Orange
    fillColor: '#241B11',
    details: {
      description: 'Cria o arquivo .code_freeze no root do projeto. O hook pre_code_freeze passa a bloquear automaticamente Edit, Write e qualquer comando git (commit, push, merge, rebase) enquanto o flag existir. Removido apenas pelo deploy_freeze(action="unset") após veredito GO.',
      parameters: ['cria: .code_freeze', 'bloqueia: Edit · Write · git commit · push · merge · rebase', 'removido por: deploy_freeze(action="unset")']
    }
  },
  {
    id: 'step-audit-shadow',
    title: '👥 Shadow Auditor',
    subtitle: 'quality_gate_sast (bandit)',
    type: 'step',
    borderColor: '#FFD54F',
    fillColor: '#201E13',
    details: {
      description: 'Executa análise estática de segurança via bandit nos arquivos Python do projeto. Retorna contagem de issues por severidade (HIGH/MEDIUM/LOW) e os top achados. Shadow raciocina sobre os resultados e emite severity + recommendation.',
      techStack: 'bandit (pip) · Python 3.12 host',
      parameters: ['tool: quality_gate_sast', 'target: arquivos .py do projeto', 'retorna: HIGH/MEDIUM/LOW counts + top issues']
    }
  },
  {
    id: 'step-audit-atlas',
    title: '👥 Atlas Auditor',
    subtitle: 'quality_gate_infra_read + api_health',
    type: 'step',
    borderColor: '#81C784',
    fillColor: '#132015',
    details: {
      description: 'Lê e valida docker-compose.yaml (healthchecks, restart policies, portas expostas) via quality_gate_infra_read. Verifica saúde HTTP dos serviços Docker (board:3001, mcp-server:8001, qdrant:6333) via quality_gate_api_health.',
      parameters: ['tools: quality_gate_infra_read + quality_gate_api_health', 'valida: healthcheck · restart_policy · HTTP status']
    }
  },
  {
    id: 'step-audit-lens',
    title: '👥 Lens Auditor',
    subtitle: 'quality_gate_api_health + log_scan',
    type: 'step',
    borderColor: '#81C784',
    fillColor: '#132015',
    details: {
      description: 'Executa health check nos endpoints HTTP e escaneia as últimas linhas do hooks_audit.log e history.json em busca de padrões CRITICAL/ERROR/WARNING. Detecta falhas de hooks, erros de agentes e eventos de infração recentes.',
      parameters: ['tools: quality_gate_api_health + quality_gate_log_scan', 'scan_window: últimas 500 linhas de log', 'padrões: CRITICAL · ERROR · WARNING · TASK_FAILURE']
    }
  },
  {
    id: 'step-reports',
    title: '[Step 3: Reports]',
    subtitle: 'severity: OK · LEVE · MÉDIA · ALTA · CRÍTICA',
    type: 'step',
    borderColor: '#2196F3', // Blue
    fillColor: '#111B24',
    details: {
      description: 'Cada especialista retorna um relatório estruturado com severity, scope, findings (dados das MCP tools) e recommendation (GO/NO_GO). O orquestrador consolida os 3 relatórios via deploy_verdict. Nenhum especialista emite veredito sem antes executar as ferramentas.',
      parameters: ['campos: severity · scope · findings · recommendation', 'severidades: OK · LEVE · MÉDIA · ALTA · CRÍTICA', 'verdade: MCP tools (não raciocínio do modelo)']
    }
  },
  {
    id: 'step-verdict-go',
    title: '✅ GO',
    subtitle: 'freeze removed → deploy authorized',
    type: 'outcome',
    borderColor: '#4CAF50', // Bright Green
    fillColor: '#112215',
    details: {
      description: 'Fires when security composite health is normal (severity ≤ MÉDIA). Unlocks file access controls and triggers release deployment scripts automatically.',
      parameters: ['remove_freeze: true', 'trigger_deploy: true']
    }
  },
  {
    id: 'step-verdict-nogo',
    title: '❌ NO_GO',
    subtitle: 'freeze maintained · human intervention required',
    type: 'outcome',
    borderColor: '#F44336', // Red
    fillColor: '#241315',
    details: {
      description: 'Fired automatically if any scan detects ALTA or CRÍTICA severity alerts. Locks development, flags evolution status as Degraded, and alerts system administrator via hooks_audit logs.',
      parameters: ['escalation: emergency-alert', 'lock_git: true']
    }
  }
];

export const HOOK_METADATA = [
  {
    id: 'hook-start',
    title: 'SessionStart → squad status inject',
    position: 'TOP',
    description: 'Triggered when a new agent session mounts. Dynamically queries agent status levels and updates current skill allocations.'
  },
  {
    id: 'hook-pre',
    title: 'PreToolUse → freeze · destructive block · schema guard',
    position: 'LEFT',
    description: 'Intercepts tool invocations. Automatically applies security checks, schemas guard verification, and blocks destructive write attempts when active freeze states are active.'
  },
  {
    id: 'hook-post',
    title: 'PostToolUse → audit log · evolution flag',
    position: 'RIGHT',
    description: 'Monitors the completion of tool commands. Commits tool audit markers to the append-only ledger and increments model evolution indices.'
  },
  {
    id: 'hook-stop',
    title: 'Stop → turn digest',
    position: 'BOTTOM',
    description: 'Runs at turn boundary completion. Aggregates operation states, formats turn digests, and issues git state preservation recommendations.'
  }
];
