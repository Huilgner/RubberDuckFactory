export interface Position {
  x: number;
  y: number;
}

export interface Size {
  width: number;
  height: number;
}

export interface DiagramNode {
  id: string;
  title: string;
  subtitle?: string;
  type: 'orchestrator' | 'mcp' | 'database' | 'agent' | 'blacklist' | 'gateway' | 'step' | 'outcome' | 'infra' | 'file';
  borderColor: string;
  fillColor: string;
  chips?: string[];
  tools?: string[];
  details?: {
    description: string;
    techStack?: string;
    parameters?: string[];
    governanceRule?: string;
  };
}

export interface SimulationLog {
  timestamp: string;
  level: 'info' | 'success' | 'warn' | 'error';
  source: string;
  message: string;
}

export interface SimulationState {
  isActive: boolean;
  currentStep: number; // 0: Idle, 1: SessionInit, 2: PreToolUse, 3: AgentExecution, 4: DeployFreeze, 5: CodeAudit, 6: ReportConsolidation, 7: VerdictGo | VerdictNoGo
  verdict: 'GO' | 'NO_GO' | null;
  logs: SimulationLog[];
  activeNodes: string[]; // List of active highlighted nodes
  activePaths: string[]; // List of active highlighted SVG connection paths
}
