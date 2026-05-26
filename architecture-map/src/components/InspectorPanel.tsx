import React from 'react';
import { DiagramNode } from '../types';
import { Settings, Info, Library, ShieldCheck, Zap } from 'lucide-react';

interface InspectorPanelProps {
  selectedNode: DiagramNode | null;
  onClose: () => void;
  onSimulateSingleNode: (nodeId: string) => void;
}

export default function InspectorPanel({
  selectedNode,
  onClose,
  onSimulateSingleNode
}: InspectorPanelProps) {
  if (!selectedNode) {
    return (
      <div className="flex flex-col h-full bg-[#0F1117] border-r border-slate-800/65 text-slate-400 p-6 justify-center items-center text-center">
        <div className="w-12 h-12 rounded-full border border-dashed border-slate-700/80 flex items-center justify-center mb-4">
          <Info className="w-6 h-6 text-slate-500" />
        </div>
        <h3 className="text-white font-display font-medium text-sm mb-1 uppercase tracking-wider">
          Node Inspector
        </h3>
        <p className="text-xs text-slate-500 max-w-[240px]">
          Click any box or component on the architecture diagram canvas to inspect its active tool parameters, APIs, and operational policies.
        </p>
      </div>
    );
  }

  return (
    <div id="inspector-panel" className="flex flex-col h-full bg-[#0F1117] border-r border-slate-800/65 text-slate-300">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-800/65 bg-[#0F1117]">
        <div className="flex items-center gap-2">
          <Settings className="w-4 h-4 text-[#CE93D8]" />
          <h3 className="font-display font-bold text-xs tracking-wider text-white uppercase">
            Inspector: {selectedNode.title.split(' ').slice(1).join(' ') || selectedNode.title}
          </h3>
        </div>
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-slate-300 text-xs px-2 py-1 bg-slate-800/60 rounded border border-slate-700 cursor-pointer"
        >
          Close
        </button>
      </div>

      {/* Body Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {/* Main Title Block */}
        <div className="p-4 rounded border border-slate-800/65 bg-[#121622] flex items-start gap-3">
          <div className="text-2xl pt-0.5 select-none text-center justify-center w-8 shrink-0">
            {selectedNode.title.split(' ')[0] || '🔧'}
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white tracking-wide">
              {selectedNode.title}
            </h4>
            {selectedNode.subtitle && (
              <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                {selectedNode.subtitle}
              </p>
            )}
            <span
              className="inline-block text-[9px] font-mono px-2 py-0.5 rounded-full mt-2"
              style={{
                backgroundColor: `${selectedNode.borderColor}15`,
                border: `1px solid ${selectedNode.borderColor}`,
                color: selectedNode.borderColor
              }}
            >
              {selectedNode.type.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Description */}
        <div className="space-y-1.5">
          <span className="text-[10px] uppercase font-mono tracking-widest text-[#4FC3F7] font-bold block">
            System Responsibility
          </span>
          <p className="text-xs text-slate-300 leading-relaxed bg-[#121622] p-3 rounded border border-slate-800/65">
            {selectedNode.details?.description || 'No direct documentation defined for this node.'}
          </p>
        </div>

        {/* Tech Stack Metadata */}
        {selectedNode.details?.techStack && (
          <div className="space-y-1.5">
            <span className="text-[10px] uppercase font-mono tracking-widest text-indigo-400 font-bold block">
              Execution / Stack Context
            </span>
            <div className="flex items-center gap-1.5 bg-[#0C0E14] p-2.5 rounded border border-slate-800/65 text-[11px] font-mono text-slate-300">
              <Library className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              <span>{selectedNode.details.techStack}</span>
            </div>
          </div>
        )}

        {/* Registered Tools */}
        {selectedNode.tools && selectedNode.tools.length > 0 && (
          <div className="space-y-1.5">
            <span className="text-[10px] uppercase font-mono tracking-widest text-emerald-400 font-bold block">
              Exposed MCP Tools
            </span>
            <div className="grid grid-cols-1 gap-1">
              {selectedNode.tools.map((tool) => (
                <div
                  key={tool}
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded border border-slate-800/65 bg-[#0C0E14] hover:bg-black/60 transition"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  <span className="text-[11px] font-mono text-emerald-300">{tool}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Custom Governance Rules or blacklists */}
        {selectedNode.details?.governanceRule && (
          <div className="space-y-1.5">
            <span className="text-[10px] uppercase font-mono tracking-widest text-amber-400 font-bold block">
              L3 Governance Restriction
            </span>
            <div className="p-3 bg-amber-950/20 border border-amber-900/50 rounded flex gap-2">
              <ShieldCheck className="w-4 h-4 text-amber-400 shrink-0" />
              <p className="text-[11px] text-slate-300 italic">
                {selectedNode.details.governanceRule}
              </p>
            </div>
          </div>
        )}

        {/* Parameters or config */}
        {selectedNode.details?.parameters && selectedNode.details.parameters.length > 0 && (
          <div className="space-y-1.5">
            <span className="text-[10px] uppercase font-mono tracking-widest text-purple-400 font-bold block">
              Parameter Bounds
            </span>
            <div className="p-3 bg-[#0C0E14] border border-slate-800/65 rounded font-mono text-[11px] space-y-1 text-purple-300">
              {selectedNode.details.parameters.map((param, index) => (
                <div key={index} className="flex justify-between border-b border-slate-900 pb-1">
                  <span>{param.split(':')[0]}</span>
                  <span className="text-slate-400 font-medium">{param.split(':')[1] || 'true'}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Direct Execute Trigger (Playground) */}
        <div className="pt-2">
          <button
            onClick={() => onSimulateSingleNode(selectedNode.id)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gradient-to-r from-teal-500/20 to-emerald-500/20 hover:from-teal-500/35 hover:to-emerald-500/35 border border-emerald-500/50 hover:border-emerald-400 rounded text-xs font-semibold text-emerald-200 cursor-pointer transition active:scale-[0.98]"
          >
            <Zap className="w-4 h-4 text-emerald-400" />
            Simulate Tool Call
          </button>
        </div>
      </div>
    </div>
  );
}
