import React, { useState, useEffect, useCallback } from 'react';
import { SYSTEM_NODES } from './data';
import { DiagramNode, SimulationLog, SimulationState } from './types';
import DiagramBoard from './components/DiagramBoard';
import InspectorPanel from './components/InspectorPanel';
import ActiveSimulationConsole from './components/ActiveSimulationConsole';
import { Layers, ShieldCheck, Cpu, Terminal, RefreshCw, LayoutGrid, Award, BookOpen } from 'lucide-react';

export default function App() {
  // UI Tabs for small screens (Mobile view routing)
  const [activeTab, setActiveTab] = useState<'diagram' | 'inspector' | 'simulator'>('diagram');
  
  // Selection and State highlights
  const [selectedNode, setSelectedNode] = useState<DiagramNode | null>(null);
  const [verdict, setVerdict] = useState<'GO' | 'NO_GO'>('GO');
  const [isInspectorOpen, setIsInspectorOpen] = useState(true);

  // Simulation timeline states
  const [simState, setSimState] = useState<SimulationState>({
    isActive: false,
    currentStep: 0,
    verdict: 'GO',
    logs: [],
    activeNodes: [],
    activePaths: []
  });

  const totalSteps = 8;

  // Logging utility inside simulation runner
  const addLog = useCallback((source: string, message: string, level: 'info' | 'success' | 'warn' | 'error' = 'info') => {
    const timeStr = new Date().toISOString().slice(11, 19) + 'Z';
    setSimState(prev => ({
      ...prev,
      logs: [...prev.logs, { timestamp: timeStr, level, source, message }]
    }));
  }, []);

  // Update SVG highlights corresponding to current state timeline level
  useEffect(() => {
    const step = simState.currentStep;
    let nodes: string[] = [];
    let paths: string[] = [];

    if (step === 0) {
      // Idle Stack
      nodes = [];
      paths = [];
    } else if (step === 1) {
      // Session Init
      nodes = ['orchestrator-claude'];
      paths = [];
    } else if (step === 2) {
      // PreToolUse Hook & Memory Server Callback
      nodes = ['orchestrator-claude', 'mcp-memory', 'db-qdrant'];
      paths = ['mcp-to-orc', 'memory-to-qdrant'];
    } else if (step === 3) {
      // OpenRouter & Agents Squad
      nodes = [
        'orchestrator-claude',
        'openrouter-gateway',
        'agent-shadow',
        'agent-chen',
        'agent-nova',
        'agent-atlas',
        'agent-lens'
      ];
      paths = ['orc-to-agents'];
    } else if (step === 4) {
      // Deploy Freeze
      nodes = ['orchestrator-claude', 'step-freeze'];
      paths = [];
    } else if (step === 5) {
      // Code Audits (Parallel checks)
      nodes = [
        'agent-shadow',
        'agent-atlas',
        'agent-lens',
        'step-audit-shadow',
        'step-audit-atlas',
        'step-audit-lens'
      ];
      paths = ['step1-to-audit'];
    } else if (step === 6) {
      // Compile reports
      nodes = ['step-reports'];
      paths = ['audit-to-reports'];
    } else if (step === 7) {
      // Release Verdict GO or NO_GO
      if (verdict === 'GO') {
        nodes = ['step-verdict-go'];
        paths = ['reports-to-go'];
      } else {
        nodes = ['step-verdict-nogo'];
        paths = ['reports-to-nogo'];
      }
    } else if (step === 8) {
      // PostToolUse, append ledger and terminate
      nodes = ['orchestrator-claude', 'mcp-quality-gate'];
      paths = [];
    }

    setSimState(prev => ({
      ...prev,
      activeNodes: nodes,
      activePaths: paths
    }));
  }, [simState.currentStep, verdict]);

  // Log outputs for the dynamic simulator state machine
  const executeLogForStep = useCallback((step: number) => {
    switch (step) {
      case 1:
        addLog('SessionStart', 'session_squad_status.py executado — estado do squad injetado no contexto.', 'info');
        addLog('Orchestrator', 'Claude Code montado. Regras de orquestração (CLAUDE.md) e L2 Skills carregadas.', 'success');
        break;
      case 2:
        addLog('PreToolUse', 'pre_code_freeze + pre_bash_guard executados. Nenhum freeze ativo detectado.', 'info');
        addLog('mcp-memory', 'recall() — buscando contexto semântico em localhost:8001...', 'info');
        addLog('Qdrant', 'REST GET /collections/memories/search — 3 matches. Status: 200 OK.', 'success');
        break;
      case 3:
        addLog('OpenRouter', 'Payload encaminhado via sovereign_proxy.py para deepseek/deepseek-chat e google/gemini-2.5-flash.', 'info');
        addLog('AgentSquad', 'Tarefas delegadas via agent_runner.py. Shadow (SecOps) e Chen (Backend) em execução paralela.', 'info');
        break;
      case 4:
        addLog('DeployCommittee', 'Orquestrador acionou skill /deploy-committee. Code Freeze solicitado.', 'warn');
        addLog('quality-gate', 'deploy_freeze(action="set") — .code_freeze criado. Edit/Write/git bloqueados pelo pre_code_freeze hook.', 'warn');
        break;
      case 5:
        addLog('quality-gate', 'Comitê acionado em paralelo: Shadow + Atlas + Lens...', 'info');
        addLog('Shadow Auditor', 'quality_gate_sast (bandit): 0 HIGH, 0 MEDIUM, 2 LOW. Severidade: OK.', 'success');
        addLog('Atlas Auditor', 'quality_gate_infra_read: docker-compose.yaml OK. quality_gate_api_health: board:3001 ✓ mcp:8001 ✓ qdrant:6333 ✓', 'success');
        addLog('Lens Auditor', 'quality_gate_log_scan: hooks_audit.log + history.json — 0 padrões CRITICAL/ERROR encontrados.', 'success');
        break;
      case 6:
        addLog('DeployCommittee', 'Consolidando relatórios via deploy_verdict()...', 'info');
        addLog('Reports', `Severity consolidada: ${verdict === 'GO' ? 'OK' : 'CRÍTICA'}. Recommendation unânime: ${verdict}.`, verdict === 'GO' ? 'info' : 'error');
        break;
      case 7:
        if (verdict === 'GO') {
          addLog('DeployVerdict', 'GO — aprovação unânime. deploy_freeze(action="unset") — .code_freeze removido.', 'success');
          addLog('System', 'Deploy autorizado. Stack disponível em localhost:3001 · localhost:8001 · localhost:6333.', 'success');
        } else {
          addLog('DeployVerdict', 'NO_GO — severidade CRÍTICA detectada. Deploy abortado. Code freeze MANTIDO.', 'error');
          addLog('System', 'Intervenção humana obrigatória. Re-executar quality gate completo após correção.', 'error');
        }
        break;
      case 8:
        addLog('PostToolUse', 'post_audit_log.py — operações do turno registradas em hooks_audit.log.', 'info');
        addLog('Ledger', 'Eventos salvos em project_ledger/history.json (append-only).', 'success');
        addLog('Stop', `stop_session_digest.py — ciclo encerrado. Evolution: ${verdict === 'GO' ? 'Stable' : 'Degraded'}. Aguardando próxima sessão.`, 'info');
        break;
    }
  }, [addLog, verdict]);

  // Main simulation clock
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    
    if (simState.isActive) {
      interval = setInterval(() => {
        setSimState(prev => {
          if (prev.currentStep >= totalSteps) {
            // Auto-loop on finish
            return {
              ...prev,
              currentStep: 0,
              logs: []
            };
          } else {
            const nextStep = prev.currentStep + 1;
            setTimeout(() => executeLogForStep(nextStep), 10);
            return {
              ...prev,
              currentStep: nextStep
            };
          }
        });
      }, 2800);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [simState.isActive, executeLogForStep]);

  // Trigger manual next step
  const handleTriggerStep = () => {
    setSimState(prev => {
      const nextStep = prev.currentStep >= totalSteps ? 1 : prev.currentStep + 1;
      const logsToKeep = prev.currentStep >= totalSteps ? [] : prev.logs;
      
      // Let the log hook execute outside state update to prevent side-effects
      setTimeout(() => executeLogForStep(nextStep), 10);
      
      return {
        ...prev,
        currentStep: nextStep,
        logs: logsToKeep
      };
    });
  };

  // Reset simulator
  const handleResetSim = () => {
    setSimState({
      isActive: false,
      currentStep: 0,
      verdict,
      logs: [],
      activeNodes: [],
      activePaths: []
    });
    addLog('System', 'Simulation timeline reset to standby.', 'info');
  };

  // Toggle run/pause
  const handleToggleActive = () => {
    setSimState(prev => {
      const nextActive = !prev.isActive;
      if (nextActive && prev.currentStep === 0) {
        // Just started auto run
        setTimeout(() => {
          addLog('System', 'Powering up simulator runtime hooks...', 'info');
          executeLogForStep(1);
        }, 10);
        return {
          ...prev,
          isActive: nextActive,
          currentStep: 1
        };
      }
      return {
        ...prev,
        isActive: nextActive
      };
    });
  };

  // Manually mock a specific node tool execution in inspector
  const handleSimulateSingleNode = (nodeId: string) => {
    const node = SYSTEM_NODES.find(n => n.id === nodeId);
    if (!node) return;
    
    // Animate node briefly
    setSimState(prev => ({
      ...prev,
      activeNodes: [...prev.activeNodes, nodeId]
    }));
    
    addLog(node.title.split(' ').slice(1).join(' ') || node.title, `Manual diagnostics call invoked. Executing default internal tool configurations.`, 'success');
    
    if (node.tools && node.tools.length > 0) {
      addLog(node.title.slice(2), `Available commands parsed: [${node.tools.join(', ')}]. Routing test token triggers... Status OK.`, 'info');
    }
    
    // Clear blink highlight after 1.5 seconds
    setTimeout(() => {
      setSimState(prev => ({
        ...prev,
        activeNodes: prev.activeNodes.filter(id => id !== nodeId)
      }));
    }, 1500);

    // Prompt mobile view change to see logs
    if (window.innerWidth < 1024) {
      setActiveTab('simulator');
    }
  };

  const handleSelectNode = (node: DiagramNode) => {
    setSelectedNode(node);
    setIsInspectorOpen(true);
    if (window.innerWidth < 1024) {
      setActiveTab('inspector');
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#0F1117] font-sans text-[#E0E0E0]">
      
      {/* Top Application Ribbon */}
      <header className="flex items-center justify-between px-6 py-3.5 bg-[#0F1117] border-b border-slate-800/65">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded bg-[#0F1117] border border-[#4FC3F7] flex items-center justify-center shadow-lg shadow-sky-500/5">
            <Layers className="w-4 h-4 text-[#4FC3F7]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-white font-display font-bold text-base tracking-wide uppercase">RubberDuckFactory</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 bg-[#2196F3]/10 text-[#4FC3F7] border border-[#4FC3F7]/20 rounded">
                L3 AGENT GRID
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">Multi-Tier Autonomous Guardrail Architecture Configuration</p>
          </div>
        </div>

        {/* Global Statistics ticker */}
        <div className="hidden md:flex items-center gap-6 text-[10px] tracking-wider uppercase font-mono bg-[#121622] px-4 py-2 rounded border border-slate-800/65 shadow-md">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>Squad: <span className="text-emerald-400 font-bold">ONLINE</span></span>
          </div>
          <div className="w-px h-4 bg-slate-800/50" />
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#FF9800]" />
            <span>Gate: <span className="text-amber-400 font-bold">{simState.currentStep === 4 || simState.currentStep === 5 ? 'LOCKED' : 'MONITORING'}</span></span>
          </div>
          <div className="w-px h-4 bg-slate-800/50" />
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-[#CE93D8]" />
            <span>Ledger: <span className="text-slate-300 font-bold">APPEND_ONLY</span></span>
          </div>
        </div>
      </header>

      {/* Main Grid Workspace */}
      <main className="flex-1 flex overflow-hidden relative">
        
        {/* Left: Collapsible Inspector Panel -- On larger screens takes the sidebar position */}
        <div
          id="sidebar-inspector"
          className={`${
            isInspectorOpen ? 'w-80' : 'w-0'
          } shrink-0 h-full transition-all duration-300 hidden lg:block overflow-hidden relative border-r border-slate-800/65`}
        >
          <InspectorPanel
            selectedNode={selectedNode}
            onClose={() => setIsInspectorOpen(false)}
            onSimulateSingleNode={handleSimulateSingleNode}
          />
        </div>

        {/* Floating toggle for inspector when closed */}
        {!isInspectorOpen && (
          <button
            onClick={() => setIsInspectorOpen(true)}
            className="absolute top-4 left-4 z-25 p-2 bg-[#161B29] hover:bg-slate-800 text-slate-200 border border-slate-700/85 rounded-md cursor-pointer shadow-lg hidden lg:flex items-center gap-1.5 transition"
          >
            <BookOpen className="w-4 h-4 text-[#CE93D8]" />
            <span className="text-xs uppercase font-semibold font-display">Inspect Node</span>
          </button>
        )}

        {/* Mobile View Tab Router */}
        <div className="flex-1 flex flex-col h-full overflow-hidden">
          {/* Tabs for mobile */}
          <div className="lg:hidden flex border-b border-slate-800 bg-[#0F1118]">
            <button
              onClick={() => setActiveTab('diagram')}
              className={`flex-1 py-3 text-xs font-semibold uppercase tracking-wider text-center border-b-2 transition ${
                activeTab === 'diagram'
                  ? 'border-[#4FC3F7] text-[#4FC3F7] bg-slate-900/40'
                  : 'border-transparent text-slate-500 hover:text-slate-300'
              }`}
            >
              Diagram Map
            </button>
            <button
              onClick={() => setActiveTab('inspector')}
              className={`flex-1 py-3 text-xs font-semibold uppercase tracking-wider text-center border-b-2 transition ${
                activeTab === 'inspector'
                  ? 'border-[#CE93D8] text-[#CE93D8] bg-slate-900/40'
                  : 'border-transparent text-slate-500 hover:text-slate-300'
              }`}
            >
              Node Inspector
            </button>
            <button
              onClick={() => setActiveTab('simulator')}
              className={`flex-1 py-3 text-xs font-semibold uppercase tracking-wider text-center border-b-2 transition ${
                activeTab === 'simulator'
                  ? 'border-[#81C784] text-[#81C784] bg-slate-900/40'
                  : 'border-transparent text-slate-500 hover:text-slate-300'
              }`}
            >
              Sim Console
            </button>
          </div>

          {/* Tab contents (Responsive Switch) */}
          <div className="flex-1 relative overflow-hidden flex">
            {/* Diagram Component - Always visible on desktop list or on active mob tab */}
            <div className={`flex-1 h-full ${activeTab === 'diagram' || window.innerWidth >= 1024 ? 'block' : 'hidden'}`}>
              <DiagramBoard
                onSelectNode={handleSelectNode}
                selectedNodeId={selectedNode?.id || null}
                activeNodes={simState.activeNodes}
                activePaths={simState.activePaths}
                simStep={simState.currentStep}
              />
            </div>

            {/* Mobile-oriented view selectors */}
            <div className={`w-full h-full lg:hidden ${activeTab === 'inspector' ? 'block' : 'hidden'}`}>
              <InspectorPanel
                selectedNode={selectedNode}
                onClose={() => setActiveTab('diagram')}
                onSimulateSingleNode={handleSimulateSingleNode}
              />
            </div>

            <div className={`w-full h-full lg:hidden ${activeTab === 'simulator' ? 'block' : 'hidden'}`}>
              <ActiveSimulationConsole
                logs={simState.logs}
                isActive={simState.isActive}
                onToggleActive={handleToggleActive}
                onReset={handleResetSim}
                currentStep={simState.currentStep}
                totalSteps={totalSteps}
                verdict={verdict}
                onSetVerdict={(v) => {
                  setVerdict(v);
                  addLog('Console', `Injected upcoming verdict release outcome: ${v}`, 'warn');
                }}
                onTriggerStep={handleTriggerStep}
              />
            </div>
          </div>
        </div>

        {/* Right Pane: Live Console logs - On larger screens */}
        <div id="simulation-panel" className="w-96 shrink-0 h-full hidden lg:block border-l border-slate-800/65">
          <ActiveSimulationConsole
            logs={simState.logs}
            isActive={simState.isActive}
            onToggleActive={handleToggleActive}
            onReset={handleResetSim}
            currentStep={simState.currentStep}
            totalSteps={totalSteps}
            verdict={verdict}
            onSetVerdict={(v) => {
              setVerdict(v);
              addLog('Console', `Verdict next outcome overridden to: ${v}`, 'warn');
            }}
            onTriggerStep={handleTriggerStep}
          />
        </div>

      </main>

    </div>
  );
}
