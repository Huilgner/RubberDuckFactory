import React, { useEffect, useRef } from 'react';
import { SimulationLog } from '../types';
import { Play, Pause, RotateCcw, ShieldAlert, Award, FileClock, Terminal } from 'lucide-react';

interface ActiveSimulationConsoleProps {
  logs: SimulationLog[];
  isActive: boolean;
  onToggleActive: () => void;
  onReset: () => void;
  currentStep: number;
  totalSteps: number;
  verdict: 'GO' | 'NO_GO' | null;
  onSetVerdict: (verdict: 'GO' | 'NO_GO') => void;
  onTriggerStep: () => void;
}

export default function ActiveSimulationConsole({
  logs,
  isActive,
  onToggleActive,
  onReset,
  currentStep,
  totalSteps,
  verdict,
  onSetVerdict,
  onTriggerStep
}: ActiveSimulationConsoleProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  const stepLabels = [
    'Idle Context',
    'SessionStart Hook',
    'PreToolUse Verify & MCP',
    'Agent Dispatching (OpenRouter)',
    'Deploy Commit: Code Freeze',
    'Deploy Commit: Parallel Audit',
    'Deploy Commit: Reports Consolidation',
    'Deploy Commit: Verdict Outcome',
    'PostToolUse & Stop Logs'
  ];

  return (
    <div id="sim-console" className="flex flex-col h-full bg-[#0F1117] border-l border-slate-800/65 text-slate-200">
      {/* Console Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-800/65 bg-[#0F1117]">
        <div className="flex items-center gap-2">
          <Terminal className="w-5 h-5 text-[#4FC3F7] animate-pulse" />
          <h2 className="font-display font-semibold text-sm tracking-wide text-white uppercase">
            Live Hook Simulator
          </h2>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 bg-slate-800 text-slate-400 rounded-full">
          v1.0.0-PROD
        </span>
      </div>

      {/* Control Actions Panel */}
      <div className="p-4 border-b border-slate-800/65 bg-[#121622] space-y-3">
        {/* Step progress bar */}
        <div>
          <div className="flex justify-between text-[11px] font-mono mb-1 text-slate-400">
            <span>Progress State: Step {currentStep} / {totalSteps}</span>
            <span className="text-[#81C784] font-semibold">{stepLabels[currentStep]}</span>
          </div>
          <div className="w-full bg-[#0F1117] h-1.5 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-[#4FC3F7] to-[#CE93D8] transition-all duration-300"
              style={{ width: `${(currentStep / totalSteps) * 100}%` }}
            />
          </div>
        </div>

        {/* Buttons */}
        <div className="flex flex-wrap gap-2 pt-1">
          <button
            id="toggle-sim"
            onClick={onToggleActive}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold cursor-pointer transition ${
              isActive
                ? 'bg-amber-600 hover:bg-amber-700 text-white'
                : 'bg-[#4FC3F7] hover:bg-[#29b6f6] text-slate-950 font-medium'
            }`}
          >
            {isActive ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            {isActive ? 'Pause Flow' : 'Auto Run'}
          </button>

          <button
            id="step-sim"
            onClick={onTriggerStep}
            disabled={isActive}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold border border-slate-700 bg-[#1A2030] text-slate-300 cursor-pointer hover:bg-[#242D45] transition disabled:opacity-40 disabled:cursor-not-allowed`}
          >
            Manual Step
          </button>

          <button
            id="reset-sim"
            onClick={onReset}
            className="flex items-center gap-1 px-3 py-1.5 rounded text-xs font-semibold border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 cursor-pointer transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset
          </button>
        </div>

        {/* Verdict Configurer (Allows the user to select outcome for Step 7) */}
        <div className="pt-2 border-t border-slate-800">
          <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-2">
            Verdict Injector (For Step 7):
          </label>
          <div className="grid grid-cols-2 gap-2">
            <button
              id="verdict-go-btn"
              onClick={() => onSetVerdict('GO')}
              className={`flex items-center justify-center gap-1 px-3 py-1.5 rounded text-xs font-mono font-bold cursor-pointer transition ${
                verdict === 'GO'
                  ? 'bg-[#4CAF50]/20 border border-[#4CAF50] text-[#81C784]'
                  : 'bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400'
              }`}
            >
              <Award className="w-3.5 h-3.5" />
              FORCE GO
            </button>
            <button
              id="verdict-nogo-btn"
              onClick={() => onSetVerdict('NO_GO')}
              className={`flex items-center justify-center gap-1 px-3 py-1.5 rounded text-xs font-mono font-bold cursor-pointer transition ${
                verdict === 'NO_GO'
                  ? 'bg-[#F44336]/20 border border-[#F44336] text-[#EF9A9A]'
                  : 'bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-400'
              }`}
            >
              <ShieldAlert className="w-3.5 h-3.5" />
              FORCE NO_GO
            </button>
          </div>
        </div>
      </div>

      {/* Logs Window */}
      <div className="flex-1 overflow-hidden flex flex-col p-4">
        <div className="flex items-center gap-1 text-[11px] font-mono text-slate-400 mb-2 uppercase tracking-wide">
          <FileClock className="w-3.5 h-3.5" />
          <span>Turn Session Audit Trail (Live)</span>
        </div>
        <div
          ref={containerRef}
          id="event-log-container"
          className="flex-1 overflow-y-auto bg-slate-950/70 border border-slate-800/80 rounded p-3 font-mono text-[11px] leading-relaxed space-y-2 select-text"
        >
          {logs.length === 0 ? (
            <div className="text-slate-500 h-full flex items-center justify-center text-center italic">
              No events triggered. click "Auto Run" or "Manual Step" to initiate the architecture lifecycle logs.
            </div>
          ) : (
            logs.map((log, idx) => (
              <div
                key={idx}
                className="flex items-start gap-1 p-1 hover:bg-slate-900/40 rounded transition-colors duration-150"
              >
                <span className="text-slate-600 shrink-0">[{log.timestamp}]</span>
                <span
                  className={`font-semibold shrink-0 ${
                    log.level === 'success'
                      ? 'text-[#81C784]'
                      : log.level === 'warn'
                      ? 'text-[#FFD54F]'
                      : log.level === 'error'
                      ? 'text-[#EF9A9A]'
                      : 'text-[#4FC3F7]'
                  }`}
                >
                  [{log.source}]
                </span>
                <span className="text-slate-300 break-all">{log.message}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
