import React, { useState, useRef, useEffect } from 'react';
import { SYSTEM_NODES, HOOK_METADATA } from '../data';
import { DiagramNode, Position } from '../types';
import { LiveAgent, EVOLUTION_COLOR } from '../hooks/useAgentData';
import { ZoomIn, ZoomOut, Maximize2, Move, HelpCircle } from 'lucide-react';

interface DiagramBoardProps {
  onSelectNode: (node: DiagramNode) => void;
  selectedNodeId: string | null;
  activeNodes: string[];
  activePaths: string[];
  simStep: number;
  liveAgents?: Record<string, LiveAgent>;
}

export default function DiagramBoard({
  onSelectNode,
  selectedNodeId,
  activeNodes,
  activePaths,
  simStep,
  liveAgents = {}
}: DiagramBoardProps) {
  // Navigation states for zooming and panning
  const [scale, setScale] = useState<number>(0.55);
  const [offset, setOffset] = useState<Position>({ x: 20, y: 15 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const dragStart = useRef<Position>({ x: 0, y: 0 });
  const viewContainerRef = useRef<HTMLDivElement>(null);

  // Zoom to fit standard screens by default
  useEffect(() => {
    if (viewContainerRef.current) {
      const width = viewContainerRef.current.clientWidth;
      if (width < 1200) {
        setScale(Math.max(width / 2400 - 0.05, 0.25));
      }
    }
  }, []);

  const handleMouseDown = (e: React.MouseEvent) => {
    // Only drag with left mouse click or middle wheel press
    if (e.button !== 0 && e.button !== 1) return;
    setIsDragging(true);
    dragStart.current = { x: e.clientX - offset.x, y: e.clientY - offset.y };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setOffset({
      x: e.clientX - dragStart.current.x,
      y: e.clientY - dragStart.current.y
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = 1.1;
    let newScale = scale;
    if (e.deltaY < 0) {
      newScale = Math.min(scale * zoomFactor, 2.5);
    } else {
      newScale = Math.max(scale / zoomFactor, 0.15);
    }
    
    // Zoom centered on raw mouse coordinate if possible
    if (viewContainerRef.current) {
      const rect = viewContainerRef.current.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      
      const xs = (mouseX - offset.x) / scale;
      const ys = (mouseY - offset.y) / scale;
      
      setScale(newScale);
      setOffset({
        x: mouseX - xs * newScale,
        y: mouseY - ys * newScale
      });
    } else {
      setScale(newScale);
    }
  };

  const resetViewport = () => {
    if (viewContainerRef.current) {
      const width = viewContainerRef.current.clientWidth;
      setScale(Math.max(width / 2450, 0.35));
      setOffset({ x: 10, y: 10 });
    }
  };

  const adjustScale = (factor: number) => {
    const newScale = Math.min(Math.max(scale * factor, 0.15), 2.5);
    setScale(newScale);
  };

  // Renderiza badge de evolution + pontos ao vivo para cada agente
  const renderLiveBadge = (nodeId: string, x: number, y: number) => {
    const live = liveAgents[nodeId];
    if (!live) return null;
    const color = EVOLUTION_COLOR[live.evolution] || '#90A4AE';
    return (
      <>
        <circle cx={x + 5} cy={y + 5} r="4" fill={color} opacity="0.9" />
        <text x={x + 14} y={y + 9} fill={color} fontSize="9.5" fontFamily="monospace" fontWeight="bold">
          {live.evolution}
        </text>
        <text x={x + 80} y={y + 9} fill="#4B5563" fontSize="9" fontFamily="monospace">
          {live.pontos.externos}ext · {live.pontos.internos}int
        </text>
      </>
    );
  };

  // Helper colors classes for background highlighting
  const getBandBgClass = (bandNum: number) => {
    switch (bandNum) {
      case 1: return simStep === 1 ? 'fill-[#121926]/90 stroke-[#4FC3F7]/50' : 'fill-[#0E1118]/80 stroke-slate-800/80';
      case 2: return [2].includes(simStep) ? 'fill-[#151421]/90 stroke-[#CE93D8]/50' : 'fill-[#0E1118]/80 stroke-slate-800/80';
      case 3: return [3].includes(simStep) ? 'fill-[#101F15]/90 stroke-[#81C784]/50' : 'fill-[#0E1118]/80 stroke-slate-800/80';
      case 4: return [4, 5, 6, 7].includes(simStep) ? 'fill-[#1C2030]/90 stroke-amber-500/40' : 'fill-[#141824]/90 stroke-slate-850/80';
      case 5: return simStep === 8 ? 'fill-[#121D24]/90 stroke-slate-700/60' : 'fill-[#0E1118]/80 stroke-slate-800/50';
      default: return 'fill-[#0E1118]/90 stroke-slate-800';
    }
  };

  return (
    <div className="relative flex-1 h-full select-none overflow-hidden bg-[#0F1117] flex flex-col">
      {/* Background Subtle Grid Overlay */}
      <div className="absolute top-4 left-4 z-10 flex flex-wrap items-center gap-2">
        <h1 className="text-xs font-bold tracking-widest text-[#E0E0E0]/90 uppercase font-display bg-[#121622] px-3.5 py-2 rounded border border-slate-800/65 flex items-center gap-2.5 shadow-lg">
          <span className="w-1.5 h-1.5 rounded-full bg-[#4FC3F7] animate-pulse" />
          RubberDuckFactory Architect
        </h1>
        <div className="flex items-center bg-[#121622]/95 border border-slate-800/65 rounded px-2.5 py-1.5 font-mono text-[10px] text-slate-400 font-semibold shadow-md gap-3">
          <span>Scale: {Math.round(scale * 100)}%</span>
          <div className="flex gap-1 border-l border-slate-800 pl-2">
            <button
              id="zoom-in"
              onClick={() => adjustScale(1.2)}
              className="p-1 hover:bg-slate-800 text-slate-300 rounded cursor-pointer transition"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              id="zoom-out"
              onClick={() => adjustScale(1 / 1.15)}
              className="p-1 hover:bg-slate-800 text-slate-300 rounded cursor-pointer transition"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              id="zoom-reset"
              onClick={resetViewport}
              className="p-1 hover:bg-slate-800 text-slate-300 rounded cursor-pointer transition"
              title="Reset View"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      <div className="absolute top-4 right-4 z-10 hidden sm:flex items-center gap-1.5 bg-[#121622]/95 border border-slate-800/65 rounded px-2.5 py-1.5 text-[9px] uppercase tracking-wider font-mono text-slate-400 shadow-md">
        <Move className="w-3.5 h-3.5" />
        <span>Drag canvas to Pan · Scroll to Zoom</span>
      </div>

      {/* SVG Canvas Workspace */}
      <div
        ref={viewContainerRef}
        id="diagram-workspace"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
        className={`flex-1 h-full w-full ${isDragging ? 'cursor-grabbing' : 'cursor-grab'} outline-none`}
      >
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 2400 1620"
          preserveAspectRatio="xMidYMid meet"
          className="w-full h-full block"
        >
          {/* Definitions and SVG patterns */}
          <defs>
            {/* Soft grid background */}
            <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
              <circle cx="12" cy="12" r="1" fill="#FFFFFF" opacity="0.05" />
            </pattern>

            {/* Neon box glow filter */}
            <filter id="neon-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            {/* Signal pulse filter */}
            <filter id="pulse-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="glow" />
              <feComponentTransfer in="glow" result="bright-glow">
                <feFuncA type="linear" slope="2" />
              </feComponentTransfer>
              <feMerge>
                <feMergeNode in="bright-glow" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            {/* Thin White Arrow markers */}
            <marker
              id="arrow-white"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="8"
              markerHeight="8"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#E2E8F0" />
            </marker>

            {/* Glowing active arrow markers */}
            <marker
              id="arrow-active"
              viewBox="0 0 10 10"
              refX="8"
              refY="5"
              markerWidth="10"
              markerHeight="10"
              orient="auto-start-reverse"
            >
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#4FC3F7" />
            </marker>
          </defs>

          {/* Render grouped layers scaled/panned */}
          <g transform={`translate(${offset.x}, ${offset.y}) scale(${scale})`}>
            
            {/* Draw grid background within constraints */}
            <rect width="2400" height="1610" fill="url(#grid)" opacity="0.8" />

            {/* Title in top-right corner */}
            <text
              x="2330"
              y="35"
              fill="#94A3B8"
              fontSize="12"
              fontFamily="monospace"
              textAnchor="end"
              fontWeight="bold"
            >
              RubberDuckFactory — System Architecture
            </text>

            {/* =======================================================
                BAND BACKGROUND PANELS 
                ======================================================= */}
            
            {/* Band 1 Background */}
            <rect
              x="30"
              y="10"
              width="2340"
              height="330"
              rx="12"
              className={`transition-all duration-300 stroke-2 ${getBandBgClass(1)}`}
            />
            <text x="50" y="40" fill="#4B5563" fontSize="11" fontFamily="sans-serif" fontWeight="bold" letterSpacing="1.5">
              BAND 1 — ORCHESTRATION & SHIELDS
            </text>

            {/* Band 2 Background */}
            <rect
              x="30"
              y="350"
              width="2340"
              height="280"
              rx="12"
              className={`transition-all duration-300 stroke-2 ${getBandBgClass(2)}`}
            />
            <text x="50" y="375" fill="#4B5563" fontSize="11" fontFamily="sans-serif" fontWeight="bold" letterSpacing="1.5">
              BAND 2 — PERSISTENT MCP SERVICES & SEMANTICS
            </text>

            {/* Band 3 Background */}
            <rect
              x="30"
              y="640"
              width="2340"
              height="350"
              rx="12"
              className={`transition-all duration-300 stroke-2 ${getBandBgClass(3)}`}
            />
            <text x="50" y="665" fill="#4B5563" fontSize="11" fontFamily="sans-serif" fontWeight="bold" letterSpacing="1.5">
              BAND 3 — AUTONOMOUS AGENT SQUAD
            </text>

            {/* Band 4 Background */}
            <rect
              x="30"
              y="1000"
              width="2340"
              height="340"
              rx="15"
              className={`transition-all duration-300 stroke-2 ${getBandBgClass(4)}`}
            />
            <text x="50" y="1030" fill="#94A3B8" fontSize="11" fontFamily="sans-serif" fontWeight="bold" letterSpacing="1.5">
              BAND 4 — RELEASE MANAGER COMITTEE (ISOLATED RUNTIME)
            </text>

            {/* Band 5 Background */}
            <rect
              x="30"
              y="1350"
              width="2340"
              height="240"
              rx="12"
              className={`transition-all duration-300 stroke-2 ${getBandBgClass(5)}`}
            />
            <text x="50" y="1375" fill="#4B5563" fontSize="11" fontFamily="sans-serif" fontWeight="bold" letterSpacing="1.5">
              BAND 5 — CONTAINER DEPLOYMENT & HISTORIC TRACEABILITY
            </text>


            {/* =======================================================
                CONNECTOR PATHS & PULSES 
                ======================================================= */}
            
            {/* Connection: memory MCP -> Orchestrator */}
            <path
              d="M 675,410 C 675,290 980,290 1020,230"
              fill="none"
              stroke={activePaths.includes('mcp-to-orc') ? '#CE93D8' : '#334155'}
              strokeWidth={activePaths.includes('mcp-to-orc') ? '2.5' : '1.5'}
              markerEnd={activePaths.includes('mcp-to-orc') ? 'url(#arrow-active)' : 'url(#arrow-white)'}
              className="transition-all duration-200"
            />
            {activePaths.includes('mcp-to-orc') && (
              <circle r="4" fill="#CE93D8" filter="url(#pulse-glow)">
                <animateMotion
                  dur="1.8s"
                  repeatCount="indefinite"
                  path="M 675,410 C 675,290 980,290 1020,230"
                />
              </circle>
            )}
            <rect x="760" y="280" width="80" height="20" rx="4" fill="#121620" stroke="#CE93D8" strokeWidth="0.5" />
            <text x="800" y="294" fill="#CE93D8" fontSize="10" fontFamily="monospace" textAnchor="middle">MCP tools</text>

            {/* Connection: quality-gate MCP -> Orchestrator */}
            <path
              d="M 1725,410 C 1725,290 1420,290 1380,230"
              fill="none"
              stroke={activePaths.includes('mcp-to-orc') ? '#4DB6AC' : '#334155'}
              strokeWidth={activePaths.includes('mcp-to-orc') ? '2.5' : '1.5'}
              markerEnd={activePaths.includes('mcp-to-orc') ? 'url(#arrow-active)' : 'url(#arrow-white)'}
              className="transition-all duration-200"
            />
            {activePaths.includes('mcp-to-orc') && (
              <circle r="4" fill="#4DB6AC" filter="url(#pulse-glow)">
                <animateMotion
                  dur="1.8s"
                  repeatCount="indefinite"
                  path="M 1725,410 C 1725,290 1420,290 1380,230"
                />
              </circle>
            )}
            <rect x="1560" y="280" width="80" height="20" rx="4" fill="#121620" stroke="#4DB6AC" strokeWidth="0.5" />
            <text x="1600" y="294" fill="#4DB6AC" fontSize="10" fontFamily="monospace" textAnchor="middle">MCP tools</text>

            {/* Connection: memory -> qdrant */}
            <path
              d="M 675,510 L 675,550"
              fill="none"
              stroke={activePaths.includes('memory-to-qdrant') ? '#CE93D8' : '#334155'}
              strokeWidth="1.5"
              markerEnd="url(#arrow-white)"
            />
            <text x="685" y="535" fill="#CE93D8" fontSize="10" fontFamily="sans-serif">embeddings</text>

            {/* Main delegation down: Claude -> OpenRouter -> Agent cards */}
            <path
              d="M 1200,230 L 1200,600"
              fill="none"
              stroke={activePaths.includes('orc-to-agents') ? '#81C784' : '#334155'}
              strokeWidth={activePaths.includes('orc-to-agents') ? '2.5' : '1.5'}
              markerEnd={activePaths.includes('orc-to-agents') ? 'url(#arrow-active)' : 'url(#arrow-white)'}
            />
            {activePaths.includes('orc-to-agents') && (
              <circle r="5" fill="#81C784" filter="url(#pulse-glow)">
                <animateMotion
                  dur="2s"
                  repeatCount="indefinite"
                  path="M 1200,230 L 1200,600"
                />
              </circle>
            )}
            <rect x="1210" y="320" width="290" height="22" rx="4" fill="#0E1118" stroke="#81C784" strokeWidth="0.5" opacity="0.9" />
            <text x="1355" y="335" fill="#81C784" fontSize="10" fontFamily="sans-serif">
              delegate tasks via agent_runner.py → OpenRouter
            </text>


            {/* =======================================================
                BAND 1 — ORCHESTRATOR & HOOKS
                ======================================================= */}
            
            {/* Deterministic Guardrails dashed shield surrounding ring */}
            <ellipse
              cx="1200"
              y="160"
              rx="530"
              ry="115"
              fill="none"
              stroke="#FF9800"
              strokeWidth="1.5"
              strokeDasharray="6,6"
              className={`${[1, 2, 8].includes(simStep) ? 'stroke-[#FF9800]' : 'stroke-[#FF9800]/25'}`}
            />
            {/* Ring Header label */}
            <text
              x="1200"
              y="38"
              fill="#FF9800"
              fontSize="12"
              fontFamily="sans-serif"
              fontWeight="bold"
              letterSpacing="1"
              textAnchor="middle"
            >
              L3 Hooks — Deterministic Guardrails
            </text>

            {/* Loop hook indicator texts */}
            {HOOK_METADATA.map((hook) => {
              const active = 
                (hook.id === 'hook-start' && simStep === 1) ||
                (hook.id === 'hook-pre' && simStep === 2) ||
                (hook.id === 'hook-post' && simStep === 8) ||
                (hook.id === 'hook-stop' && simStep === 8);
              
              let tx = 1200, ty = 160;
              let anchor = "middle";
              
              if (hook.position === 'TOP') { tx = 1200; ty = 69; anchor="middle"; }
              else if (hook.position === 'LEFT') { tx = 650; ty = 165; anchor="end"; }
              else if (hook.position === 'RIGHT') { tx = 1750; ty = 165; anchor="start"; }
              else if (hook.position === 'BOTTOM') { tx = 1200; ty = 295; anchor="middle"; }

              return (
                <g key={hook.id} className="transition-all duration-300">
                  <rect
                    x={anchor === 'middle' ? tx - 160 : anchor === 'end' ? tx - 310 : tx + 10}
                    y={ty - 16}
                    width={anchor === 'middle' ? 320 : 300}
                    height={22}
                    rx="4"
                    fill={active ? '#FF9800' : '#141824'}
                    stroke={active ? '#FFE082' : '#374151'}
                    strokeWidth="0.5"
                    opacity={active ? 1 : 0.45}
                  />
                  <text
                    x={tx}
                    y={ty - 1}
                    fill={active ? '#0F1117' : '#FFA726'}
                    fontSize="10"
                    fontFamily="monospace"
                    fontWeight={active ? 'bold' : 'normal'}
                    textAnchor={anchor}
                    className="cursor-help"
                    title={hook.description}
                  >
                    {hook.title}
                  </text>
                </g>
              );
            })}

            {/* Orchestrator Master Box (Claude) */}
            {(() => {
              const node = SYSTEM_NODES.find(n => n.id === 'orchestrator-claude')!;
              const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
              return (
                <g
                  transform="translate(900, 105)"
                  className="cursor-pointer transition duration-200"
                  onClick={() => onSelectNode(node)}
                >
                  <rect
                    width="600"
                    height="110"
                    rx="10"
                    fill={node.fillColor}
                    stroke={node.borderColor}
                    strokeWidth={active ? 3 : 1.5}
                    filter={active ? 'url(#neon-glow)' : undefined}
                  />
                  <text x="40" y="35" fill="#FFFFFF" fontSize="18" fontFamily="sans-serif" fontWeight="bold">
                    {node.title}
                  </text>
                  <text x="40" y="58" fill="#90A4AE" fontSize="11" fontFamily="sans-serif">
                    {node.subtitle}
                  </text>
                  {/* Small chips */}
                  <g transform="translate(40, 75)">
                    <rect x="0" y="0" width="520" height="22" rx="4" fill="#242C3A" stroke="#455A64" strokeWidth="0.5" />
                    <text x="12" y="14" fill="#CFD8DC" fontSize="10" fontFamily="monospace">
                      [L2 Skills: agent-briefing · deploy-committee · ledger-log · governance-check]
                    </text>
                  </g>
                </g>
              );
            })()}


            {/* =======================================================
                BAND 2 — MCP SERVERS
                ======================================================= */}
            
            {/* rubberduck-memory Box */}
            {(() => {
              const node = SYSTEM_NODES.find(n => n.id === 'mcp-memory')!;
              const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
              return (
                <g
                  transform="translate(450, 390)"
                  className="cursor-pointer"
                  onClick={() => onSelectNode(node)}
                >
                  <rect
                    width="450"
                    height="125"
                    rx="8"
                    fill={node.fillColor}
                    stroke={node.borderColor}
                    strokeWidth={active ? 2.5 : 1.5}
                    filter={active ? 'url(#neon-glow)' : undefined}
                  />
                  <text x="25" y="32" fill="#E1BEE7" fontSize="15" fontFamily="sans-serif" fontWeight="bold">
                    {node.title}
                  </text>
                  <text x="25" y="52" fill="#B0BEC5" fontSize="11" fontFamily="sans-serif">
                    {node.subtitle}
                  </text>
                  {/* Monospace tools inside */}
                  <g transform="translate(25, 68)">
                    {node.tools?.map((tool, idx) => (
                      <g key={tool} transform={`translate(${idx * 90}, 0)`}>
                        <rect width="80" height="20" rx="4" fill="#251F33" stroke="#CE93D8" strokeWidth="0.5" />
                        <text x="40" y="14" fill="#E1BEE7" fontSize="10" fontFamily="monospace" textAnchor="middle">
                          {tool}
                        </text>
                      </g>
                    ))}
                  </g>
                </g>
              );
            })()}

            {/* Qdrant Badge below */}
            {(() => {
              const node = SYSTEM_NODES.find(n => n.id === 'db-qdrant')!;
              const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
              return (
                <g
                  transform="translate(525, 550)"
                  className="cursor-pointer"
                  onClick={() => onSelectNode(node)}
                >
                  <rect
                    width="300"
                    height="40"
                    rx="6"
                    fill={node.fillColor}
                    stroke={node.borderColor}
                    strokeWidth={active ? 2.5 : 1.5}
                  />
                  <text x="150" y="24" fill="#CE93D8" fontSize="11" fontFamily="monospace" fontWeight="bold" textAnchor="middle">
                    🔵 Qdrant (vector DB · localhost:6333)
                  </text>
                </g>
              );
            })()}

            {/* rubberduck-quality-gate Box */}
            {(() => {
              const node = SYSTEM_NODES.find(n => n.id === 'mcp-quality-gate')!;
              const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
              return (
                <g
                  transform="translate(1410, 390)"
                  className="cursor-pointer"
                  onClick={() => onSelectNode(node)}
                >
                  <rect
                    width="540"
                    height="190"
                    rx="8"
                    fill={node.fillColor}
                    stroke={node.borderColor}
                    strokeWidth={active ? 2.5 : 1.5}
                    filter={active ? 'url(#neon-glow)' : undefined}
                  />
                  <text x="25" y="32" fill="#B2DFDB" fontSize="15" fontFamily="sans-serif" fontWeight="bold">
                    {node.title}
                  </text>
                  <text x="25" y="52" fill="#B0BEC5" fontSize="11" fontFamily="sans-serif">
                    {node.subtitle}
                  </text>
                  {/* Monospace tools inside */}
                  <g transform="translate(25, 72)">
                    {/* Row 1 tools */}
                    <g transform="translate(0, 0)">
                      <rect width="150" height="20" rx="4" fill="#1C302D" stroke="#4DB6AC" strokeWidth="0.5" />
                      <text x="75" y="14" fill="#E0F2F1" fontSize="10" fontFamily="monospace" textAnchor="middle">deploy_freeze</text>
                    </g>
                    <g transform="translate(165, 0)">
                      <rect width="150" height="20" rx="4" fill="#1C302D" stroke="#4DB6AC" strokeWidth="0.5" />
                      <text x="75" y="14" fill="#E0F2F1" fontSize="10" fontFamily="monospace" textAnchor="middle">quality_gate_sast</text>
                    </g>
                    <g transform="translate(330, 0)">
                      <rect width="160" height="20" rx="4" fill="#1C302D" stroke="#4DB6AC" strokeWidth="0.5" />
                      <text x="80" y="14" fill="#E0F2F1" fontSize="10" fontFamily="monospace" textAnchor="middle">quality_gate_infra_read</text>
                    </g>

                    {/* Row 2 tools */}
                    <g transform="translate(0, 32)">
                      <rect width="150" height="20" rx="4" fill="#1C302D" stroke="#4DB6AC" strokeWidth="0.5" />
                      <text x="75" y="14" fill="#E0F2F1" fontSize="10" fontFamily="monospace" textAnchor="middle">quality_gate_api_health</text>
                    </g>
                    <g transform="translate(165, 32)">
                      <rect width="150" height="20" rx="4" fill="#1C302D" stroke="#4DB6AC" strokeWidth="0.5" />
                      <text x="75" y="14" fill="#E0F2F1" fontSize="10" fontFamily="monospace" textAnchor="middle">quality_gate_log_scan</text>
                    </g>
                    <g transform="translate(330, 32)">
                      <rect width="160" height="20" rx="4" fill="#1C302D" stroke="#4DB6AC" strokeWidth="0.5" />
                      <text x="80" y="14" fill="#E0F2F1" fontSize="10" fontFamily="monospace" textAnchor="middle">deploy_verdict</text>
                    </g>
                  </g>
                </g>
              );
            })()}


            {/* =======================================================
                BAND 3 — AGENT SQUAD
                ======================================================= */}
            
            {/* OpenRouter Gateway Box */}
            {(() => {
              const node = SYSTEM_NODES.find(n => n.id === 'openrouter-gateway')!;
              const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
              return (
                <g
                  transform="translate(1050, 605)"
                  className="cursor-pointer"
                  onClick={() => onSelectNode(node)}
                >
                  <rect
                    width="300"
                    height="45"
                    rx="6"
                    fill={node.fillColor}
                    stroke={node.borderColor}
                    strokeWidth={active ? 2.5 : 1}
                  />
                  <text x="150" y="27" fill="#ECEFF1" fontSize="12" fontFamily="sans-serif" fontWeight="bold" textAnchor="middle">
                    🌐 OpenRouter (unified LLM gateway)
                  </text>
                </g>
              );
            })()}

            {/* Connected route below OpenRouter to Squad main row */}
            <path
              d="M 1200,650 L 1200,685"
              fill="none"
              stroke={activePaths.includes('orc-to-agents') ? '#81C784' : '#334155'}
              strokeWidth="1.5"
            />

            {/* TIER 3 — Specialist Box Container */}
            <g transform="translate(130, 690)">
              <rect width="360" height="150" rx="8" fill="#141824/60" stroke="#FFD54F" strokeWidth="1" strokeDasharray="4,4" />
              <text x="15" y="-6" fill="#FFD54F" fontSize="11" fontFamily="sans-serif" fontWeight="bold">
                T3 Specialist
              </text>
              {(() => {
                const node = SYSTEM_NODES.find(n => n.id === 'agent-shadow')!;
                const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
                return (
                  <g
                    transform="translate(15, 20)"
                    className="cursor-pointer"
                    onClick={() => onSelectNode(node)}
                  >
                    <rect
                      width="330"
                      height="110"
                      rx="6"
                      fill={node.fillColor}
                      stroke={node.borderColor}
                      strokeWidth={active ? 2.5 : 1}
                      filter={active ? 'url(#neon-glow)' : undefined}
                    />
                    <text x="20" y="32" fill="#FFFFFF" fontSize="14" fontFamily="sans-serif" fontWeight="bold">
                      {node.title}
                    </text>
                    <text x="20" y="52" fill="#FFE082" fontSize="10" fontFamily="monospace">
                      gemini-2.5-pro
                    </text>
                    <text x="20" y="72" fill="#90A4AE" fontSize="11" fontFamily="sans-serif">
                      Backend & Security
                    </text>
                    <rect x="20" y="82" width="65" height="18" rx="3" fill="#FFE082" opacity="0.15" />
                    <text x="52" y="94" fill="#FFD54F" fontSize="10" fontFamily="sans-serif" fontWeight="bold" textAnchor="middle">
                      SecOps ★
                    </text>
                  </g>
                );
              })()}
              {renderLiveBadge('agent-shadow', 15, 135)}
            </g>

            {/* TIER 2 — Operator Box Container */}
            <g transform="translate(515, 690)">
              <rect width="1140" height="150" rx="8" fill="#141824/60" stroke="#81C784" strokeWidth="1" strokeDasharray="4,4" />
              <text x="15" y="-6" fill="#81C784" fontSize="11" fontFamily="sans-serif" fontWeight="bold">
                T2 Operator
              </text>

              {/* Chen */}
              {(() => {
                const node = SYSTEM_NODES.find(n => n.id === 'agent-chen')!;
                const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
                return (
                  <g
                    transform="translate(15, 20)"
                    className="cursor-pointer"
                    onClick={() => onSelectNode(node)}
                  >
                    <rect width="260" height="110" rx="6" fill={node.fillColor} stroke={node.borderColor} strokeWidth={active ? 2.5 : 1} filter={active ? 'url(#neon-glow)' : undefined} />
                    <text x="20" y="35" fill="#FFFFFF" fontSize="14" fontFamily="sans-serif" fontWeight="bold">{node.title}</text>
                    <text x="20" y="55" fill="#A5D6A7" fontSize="10" fontFamily="monospace">deepseek-chat</text>
                    <text x="20" y="80" fill="#90A4AE" fontSize="11" fontFamily="sans-serif">Backend Eng</text>
                  </g>
                );
              })()}

              {/* Nova */}
              {(() => {
                const node = SYSTEM_NODES.find(n => n.id === 'agent-nova')!;
                const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
                return (
                  <g
                    transform="translate(295, 20)"
                    className="cursor-pointer"
                    onClick={() => onSelectNode(node)}
                  >
                    <rect width="260" height="110" rx="6" fill={node.fillColor} stroke={node.borderColor} strokeWidth={active ? 2.5 : 1} filter={active ? 'url(#neon-glow)' : undefined} />
                    <text x="20" y="35" fill="#FFFFFF" fontSize="14" fontFamily="sans-serif" fontWeight="bold">{node.title}</text>
                    <text x="20" y="55" fill="#A5D6A7" fontSize="10" fontFamily="monospace">gemini-2.5-flash</text>
                    <text x="20" y="80" fill="#90A4AE" fontSize="11" fontFamily="sans-serif">Frontend Dev</text>
                  </g>
                );
              })()}

              {/* Atlas */}
              {(() => {
                const node = SYSTEM_NODES.find(n => n.id === 'agent-atlas')!;
                const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
                return (
                  <g
                    transform="translate(575, 20)"
                    className="cursor-pointer"
                    onClick={() => onSelectNode(node)}
                  >
                    <rect width="260" height="110" rx="6" fill={node.fillColor} stroke={node.borderColor} strokeWidth={active ? 2.5 : 1} filter={active ? 'url(#neon-glow)' : undefined} />
                    <text x="20" y="35" fill="#FFFFFF" fontSize="14" fontFamily="sans-serif" fontWeight="bold">{node.title}</text>
                    <text x="20" y="55" fill="#A5D6A7" fontSize="10" fontFamily="monospace">gemini-2.5-flash</text>
                    <text x="20" y="80" fill="#90A4AE" fontSize="11" fontFamily="sans-serif">SRE & Infra</text>
                  </g>
                );
              })()}

              {/* Lens */}
              {(() => {
                const node = SYSTEM_NODES.find(n => n.id === 'agent-lens')!;
                const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
                return (
                  <g
                    transform="translate(855, 20)"
                    className="cursor-pointer"
                    onClick={() => onSelectNode(node)}
                  >
                    <rect width="270" height="110" rx="6" fill={node.fillColor} stroke={node.borderColor} strokeWidth={active ? 2.5 : 1} filter={active ? 'url(#neon-glow)' : undefined} />
                    <text x="20" y="35" fill="#FFFFFF" fontSize="14" fontFamily="sans-serif" fontWeight="bold">{node.title}</text>
                    <text x="20" y="55" fill="#A5D6A7" fontSize="10" fontFamily="monospace">deepseek-chat</text>
                    <text x="20" y="80" fill="#90A4AE" fontSize="11" fontFamily="sans-serif">QA & Observability</text>
                  </g>
                );
              })()}
              {renderLiveBadge('agent-chen',  15,  135)}
              {renderLiveBadge('agent-nova',  295, 135)}
              {renderLiveBadge('agent-atlas', 575, 135)}
              {renderLiveBadge('agent-lens',  855, 135)}
            </g>

            {/* TIER 1 — Observer Box Container */}
            <g transform="translate(1675, 690)">
              <rect width="590" height="150" rx="8" fill="#141824/60" stroke="#B0BEC5" strokeWidth="1" strokeDasharray="4,4" />
              <text x="15" y="-6" fill="#B0BEC5" fontSize="11" fontFamily="sans-serif" fontWeight="bold">
                T1 Observer
              </text>

              {/* Phoenix */}
              {(() => {
                const node = SYSTEM_NODES.find(n => n.id === 'agent-phoenix')!;
                const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
                return (
                  <g
                    transform="translate(15, 20)"
                    className="cursor-pointer"
                    onClick={() => onSelectNode(node)}
                  >
                    <rect width="175" height="110" rx="6" fill={node.fillColor} stroke={node.borderColor} strokeWidth={active ? 2.5 : 1} filter={active ? 'url(#neon-glow)' : undefined} />
                    <text x="15" y="32" fill="#FFFFFF" fontSize="13" fontFamily="sans-serif" fontWeight="bold">{node.title}</text>
                    <text x="15" y="52" fill="#CFD8DC" fontSize="10" fontFamily="monospace">claude-opus-4</text>
                    <text x="15" y="80" fill="#90A4AE" fontSize="11" fontFamily="sans-serif">Elixir/OTP</text>
                  </g>
                );
              })()}

              {/* Falcon */}
              {(() => {
                const node = SYSTEM_NODES.find(n => n.id === 'agent-falcon')!;
                const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
                return (
                  <g
                    transform="translate(205, 20)"
                    className="cursor-pointer"
                    onClick={() => onSelectNode(node)}
                  >
                    <rect width="175" height="110" rx="6" fill={node.fillColor} stroke={node.borderColor} strokeWidth={active ? 2.5 : 1} filter={active ? 'url(#neon-glow)' : undefined} />
                    <text x="15" y="32" fill="#FFFFFF" fontSize="13" fontFamily="sans-serif" fontWeight="bold">{node.title}</text>
                    <text x="15" y="52" fill="#CFD8DC" fontSize="10" fontFamily="monospace">gemini-lite</text>
                    <text x="15" y="80" fill="#90A4AE" fontSize="11" fontFamily="sans-serif">Documentation</text>
                  </g>
                );
              })()}

              {/* Quill */}
              {(() => {
                const node = SYSTEM_NODES.find(n => n.id === 'agent-quill')!;
                const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
                return (
                  <g
                    transform="translate(395, 20)"
                    className="cursor-pointer"
                    onClick={() => onSelectNode(node)}
                  >
                    <rect width="180" height="110" rx="6" fill={node.fillColor} stroke={node.borderColor} strokeWidth={active ? 2.5 : 1} filter={active ? 'url(#neon-glow)' : undefined} />
                    <text x="15" y="32" fill="#FFFFFF" fontSize="13" fontFamily="sans-serif" fontWeight="bold">{node.title}</text>
                    <text x="15" y="52" fill="#CFD8DC" fontSize="10" fontFamily="monospace">deepseek-free</text>
                    <text x="15" y="80" fill="#90A4AE" fontSize="11" fontFamily="sans-serif">Tech Docs</text>
                  </g>
                );
              })()}
              {renderLiveBadge('agent-phoenix', 15,  135)}
              {renderLiveBadge('agent-falcon',  205, 135)}
              {renderLiveBadge('agent-quill',   395, 135)}
            </g>

            {/* Blacklist Section centered below */}
            {(() => {
              const node = SYSTEM_NODES.find(n => n.id === 'blacklist-echo')!;
              const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
              return (
                <g
                  transform="translate(850, 885)"
                  className="cursor-pointer"
                  onClick={() => onSelectNode(node)}
                >
                  <rect
                    width="700"
                    height="45"
                    rx="6"
                    fill={node.fillColor}
                    stroke={node.borderColor}
                    strokeWidth={active ? 2.5 : 1}
                  />
                  <text x="350" y="27" fill="#EF9A9A" fontSize="12" fontFamily="monospace" fontWeight="bold" textAnchor="middle">
                    🚫 agents/blacklist/ — Echo (dismissed: hallucination in production)
                  </text>
                </g>
              );
            })()}


            {/* =======================================================
                BAND 4 — DEPLOY COMMITTEE RELEASE MANAGER FLOW
                ======================================================= */}
            
            {/* Overlay Panel background color inner */}
            <rect
              x="100"
              y="1010"
              width="2200"
              height="310"
              rx="12"
              fill="#1A1F2E"
              stroke="#2A354F"
              strokeWidth="0.5"
            />
            
            {/* Panel Header */}
            <text x="130" y="1045" fill="#FFFFFF" fontSize="14" fontFamily="sans-serif" fontWeight="bold">
              🚀 Deploy Committee — Release Manager Flow
            </text>

            {/* Step 1: Code Freeze Box */}
            {(() => {
              const node = SYSTEM_NODES.find(n => n.id === 'step-freeze')!;
              const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
              return (
                <g
                  transform="translate(130, 1100)"
                  className="cursor-pointer"
                  onClick={() => onSelectNode(node)}
                >
                  <rect
                    width="350"
                    height="100"
                    rx="8"
                    fill={node.fillColor}
                    stroke={node.borderColor}
                    strokeWidth={active ? 2.5 : 1.5}
                    filter={active ? 'url(#neon-glow)' : undefined}
                  />
                  <text x="25" y="32" fill="#FFA726" fontSize="14" fontFamily="sans-serif" fontWeight="bold">
                    {node.title}
                  </text>
                  <text x="25" y="58" fill="#FFF" fontSize="12" fontFamily="monospace">
                    {node.subtitle}
                  </text>
                  <text x="25" y="80" fill="#FFE082" fontSize="11" fontFamily="sans-serif">
                    blocks Edit · Write · git
                  </text>
                </g>
              );
            })()}

            {/* Arrows from Step 1 Splitting to 3 audit files */}
            <path
              d="M 480,1150 C 530,1150 530,1075 580,1075"
              fill="none"
              stroke={activePaths.includes('step1-to-audit') ? '#FFA726' : '#475569'}
              strokeWidth={activePaths.includes('step1-to-audit') ? '2.5' : '1.5'}
              markerEnd={activePaths.includes('step1-to-audit') ? 'url(#arrow-active)' : 'url(#arrow-white)'}
            />
            <path
              d="M 480,1150 L 580,1150"
              fill="none"
              stroke={activePaths.includes('step1-to-audit') ? '#FFA726' : '#475569'}
              strokeWidth={activePaths.includes('step1-to-audit') ? '2.5' : '1.5'}
              markerEnd={activePaths.includes('step1-to-audit') ? 'url(#arrow-active)' : 'url(#arrow-white)'}
            />
            <path
              d="M 480,1150 C 530,1150 530,1225 580,1225"
              fill="none"
              stroke={activePaths.includes('step1-to-audit') ? '#FFA726' : '#475569'}
              strokeWidth={activePaths.includes('step1-to-audit') ? '2.5' : '1.5'}
              markerEnd={activePaths.includes('step1-to-audit') ? 'url(#arrow-active)' : 'url(#arrow-white)'}
            />

            {/* Glowing signal particles splitting */}
            {activePaths.includes('step1-to-audit') && (
              <>
                <circle r="4.5" fill="#FFA726" filter="url(#pulse-glow)">
                  <animateMotion dur="1s" repeatCount="indefinite" path="M 480,1150 C 530,1150 530,1075 580,1075" />
                </circle>
                <circle r="4.5" fill="#FFA726" filter="url(#pulse-glow)">
                  <animateMotion dur="1s" repeatCount="indefinite" path="M 480,1150 L 580,1150" />
                </circle>
                <circle r="4.5" fill="#FFA726" filter="url(#pulse-glow)">
                  <animateMotion dur="1s" repeatCount="indefinite" path="M 480,1150 C 530,1150 530,1225 580,1225" />
                </circle>
              </>
            )}

            {/* Step 2: Parallel Audits (3 stacked boxes) */}
            {/* Shadow Auditor (SAST bandit) */}
            {(() => {
              const node = SYSTEM_NODES.find(n => n.id === 'step-audit-shadow')!;
              const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
              return (
                <g
                  transform="translate(580, 1050)"
                  className="cursor-pointer"
                  onClick={() => onSelectNode(node)}
                >
                  <rect
                    width="420"
                    height="50"
                    rx="6"
                    fill={node.fillColor}
                    stroke={node.borderColor}
                    strokeWidth={active ? 2.5 : 1}
                    filter={active ? 'url(#neon-glow)' : undefined}
                  />
                  <text x="15" y="24" fill="#FFE082" fontSize="11" fontFamily="sans-serif" fontWeight="bold">
                    Shadow — quality_gate_sast (bandit)
                  </text>
                  <text x="15" y="40" fill="#90A4AE" fontSize="9" fontFamily="monospace">
                    Backend Security SAST
                  </text>
                </g>
              );
            })()}

            {/* Atlas Auditor */}
            {(() => {
              const node = SYSTEM_NODES.find(n => n.id === 'step-audit-atlas')!;
              const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
              return (
                <g
                  transform="translate(580, 1125)"
                  className="cursor-pointer"
                  onClick={() => onSelectNode(node)}
                >
                  <rect
                    width="420"
                    height="50"
                    rx="6"
                    fill={node.fillColor}
                    stroke={node.borderColor}
                    strokeWidth={active ? 2.5 : 1}
                    filter={active ? 'url(#neon-glow)' : undefined}
                  />
                  <text x="15" y="24" fill="#A5D6A7" fontSize="11" fontFamily="sans-serif" fontWeight="bold">
                    Atlas — quality_gate_infra_read + api_health
                  </text>
                  <text x="15" y="40" fill="#90A4AE" fontSize="9" fontFamily="monospace">
                    Infrastructure & Container Validation
                  </text>
                </g>
              );
            })()}

            {/* Lens Auditor */}
            {(() => {
              const node = SYSTEM_NODES.find(n => n.id === 'step-audit-lens')!;
              const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
              return (
                <g
                  transform="translate(580, 1200)"
                  className="cursor-pointer"
                  onClick={() => onSelectNode(node)}
                >
                  <rect
                    width="420"
                    height="50"
                    rx="6"
                    fill={node.fillColor}
                    stroke={node.borderColor}
                    strokeWidth={active ? 2.5 : 1}
                    filter={active ? 'url(#neon-glow)' : undefined}
                  />
                  <text x="15" y="24" fill="#A5D6A7" fontSize="11" fontFamily="sans-serif" fontWeight="bold">
                    Lens — quality_gate_api_health + log_scan
                  </text>
                  <text x="15" y="40" fill="#90A4AE" fontSize="9" fontFamily="monospace">
                    QA & Active log analyzer
                  </text>
                </g>
              );
            })()}

            {/* Convergence Arrows to Reports consolidation */}
            <path
              d="M 1000,1075 C 1050,1075 1050,1150 1100,1150"
              fill="none"
              stroke={activePaths.includes('audit-to-reports') ? '#4FC3F7' : '#475569'}
              strokeWidth={activePaths.includes('audit-to-reports') ? '2.5' : '1.5'}
              markerEnd={activePaths.includes('audit-to-reports') ? 'url(#arrow-active)' : 'url(#arrow-white)'}
            />
            <path
              d="M 1000,1150 L 1100,1150"
              fill="none"
              stroke={activePaths.includes('audit-to-reports') ? '#4FC3F7' : '#475569'}
              strokeWidth={activePaths.includes('audit-to-reports') ? '2.5' : '1.5'}
              markerEnd={activePaths.includes('audit-to-reports') ? 'url(#arrow-active)' : 'url(#arrow-white)'}
            />
            <path
              d="M 1000,1225 C 1050,1225 1050,1150 1100,1150"
              fill="none"
              stroke={activePaths.includes('audit-to-reports') ? '#4FC3F7' : '#475569'}
              strokeWidth={activePaths.includes('audit-to-reports') ? '2.5' : '1.5'}
              markerEnd={activePaths.includes('audit-to-reports') ? 'url(#arrow-active)' : 'url(#arrow-white)'}
            />

            {activePaths.includes('audit-to-reports') && (
              <>
                <circle r="4" fill="#4FC3F7" filter="url(#pulse-glow)">
                  <animateMotion dur="1s" repeatCount="indefinite" path="M 1000,1075 C 1050,1075 1050,1150 1100,1150" />
                </circle>
                <circle r="4" fill="#4FC3F7" filter="url(#pulse-glow)">
                  <animateMotion dur="1s" repeatCount="indefinite" path="M 1000,1150 L 1100,1150" />
                </circle>
                <circle r="4" fill="#4FC3F7" filter="url(#pulse-glow)">
                  <animateMotion dur="1s" repeatCount="indefinite" path="M 1000,1225 C 1050,1225 1050,1150 1100,1150" />
                </circle>
              </>
            )}

            {/* Step 3: Reports consolication Box */}
            {(() => {
              const node = SYSTEM_NODES.find(n => n.id === 'step-reports')!;
              const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
              return (
                <g
                  transform="translate(1100, 1100)"
                  className="cursor-pointer"
                  onClick={() => onSelectNode(node)}
                >
                  <rect
                    width="400"
                    height="100"
                    rx="8"
                    fill={node.fillColor}
                    stroke={node.borderColor}
                    strokeWidth={active ? 2.5 : 1.5}
                    filter={active ? 'url(#neon-glow)' : undefined}
                  />
                  <text x="25" y="32" fill="#64B5F6" fontSize="14" fontFamily="sans-serif" fontWeight="bold">
                    {node.title}
                  </text>
                  <text x="25" y="58" fill="#ECEFF1" fontSize="11" fontFamily="monospace">
                    severity: OK · LEVE · MÉDIA · ALTA · CRÍTICA
                  </text>
                  <text x="25" y="80" fill="#90CAF9" fontSize="11" fontFamily="monospace" fontWeight="semibold">
                    recommendation: GO · NO_GO
                  </text>
                </g>
              );
            })()}

            {/* Split from Reports to Outcomes GO and NO_GO */}
            <path
              d="M 1500,1150 C 1550,1150 1550,1095 1600,1095"
              fill="none"
              stroke={activePaths.includes('reports-to-go') ? '#4CAF50' : '#475569'}
              strokeWidth={activePaths.includes('reports-to-go') ? '3' : '1.5'}
              markerEnd={activePaths.includes('reports-to-go') ? 'url(#arrow-active)' : 'url(#arrow-white)'}
            />
            <path
              d="M 1500,1150 C 1550,1150 1550,1205 1600,1205"
              fill="none"
              stroke={activePaths.includes('reports-to-nogo') ? '#F44336' : '#475569'}
              strokeWidth={activePaths.includes('reports-to-nogo') ? '3' : '1.5'}
              markerEnd={activePaths.includes('reports-to-nogo') ? 'url(#arrow-active)' : 'url(#arrow-white)'}
            />

            {/* Dynamic glowing verdict routing particle */}
            {activePaths.includes('reports-to-go') && (
              <circle r="5" fill="#4CAF50" filter="url(#pulse-glow)">
                <animateMotion dur="1s" repeatCount="indefinite" path="M 1500,1150 C 1550,1150 1550,1095 1600,1095" />
              </circle>
            )}
            {activePaths.includes('reports-to-nogo') && (
              <circle r="5" fill="#F44336" filter="url(#pulse-glow)">
                <animateMotion dur="1s" repeatCount="indefinite" path="M 1500,1150 C 1550,1150 1550,1205 1600,1205" />
              </circle>
            )}

            {/* Step 4: Verdict outcomes */}
            {/* Verdict GO */}
            {(() => {
              const node = SYSTEM_NODES.find(n => n.id === 'step-verdict-go')!;
              const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
              return (
                <g
                  transform="translate(1600, 1060)"
                  className="cursor-pointer"
                  onClick={() => onSelectNode(node)}
                >
                  <rect
                    width="620"
                    height="60"
                    rx="6"
                    fill={node.fillColor}
                    stroke={node.borderColor}
                    strokeWidth={active ? 3 : 1.5}
                    filter={active ? 'url(#neon-glow)' : undefined}
                  />
                  <text x="25" y="35" fill="#81C784" fontSize="14" fontFamily="sans-serif" fontWeight="bold">
                    {node.title} — freeze removed → deploy authorized
                  </text>
                </g>
              );
            })()}

            {/* Verdict NO_GO */}
            {(() => {
              const node = SYSTEM_NODES.find(n => n.id === 'step-verdict-nogo')!;
              const active = activeNodes.includes(node.id) || selectedNodeId === node.id;
              return (
                <g
                  transform="translate(1600, 1145)"
                  className="cursor-pointer"
                  onClick={() => onSelectNode(node)}
                >
                  <rect
                    width="620"
                    height="90"
                    rx="6"
                    fill={node.fillColor}
                    stroke={node.borderColor}
                    strokeWidth={active ? 3 : 1.5}
                    filter={active ? 'url(#neon-glow)' : undefined}
                  />
                  <text x="25" y="32" fill="#E57373" fontSize="14" fontFamily="sans-serif" fontWeight="bold">
                    {node.title} — freeze maintained · human intervention required
                  </text>
                  <text x="25" y="62" fill="#EF9A9A" fontSize="11" fontFamily="sans-serif">
                    (auto-triggered by verification failures or severity ALTA or CRÍTICA)
                  </text>
                </g>
              );
            })()}


            {/* =======================================================
                BAND 5 — INFRASTRUCTURE & GOVERNANCE
                ======================================================= */}
            
            {/* Left Panel: Docker Stack */}
            <g transform="translate(130, 1400)">
              <rect width="1020" height="150" rx="8" fill="#111520" stroke="#475569" strokeWidth="1" />
              <text x="20" y="-6" fill="#94A3B8" fontSize="11" fontFamily="sans-serif" fontWeight="bold">Custom Docker Stack</text>

              {/* Grid 2x2 Services */}
              {/* board */}
              <g transform="translate(20, 25)">
                <rect width="470" height="45" rx="4" fill="#1C2132" stroke="#475569" strokeWidth="0.5" />
                <text x="15" y="27" fill="#ECEFF1" fontSize="11" fontFamily="monospace">
                  board (Next.js · :3001) <tspan fill="#4FC3F7">● RUNNING</tspan>
                </text>
              </g>

              {/* qdrant */}
              <g transform="translate(515, 25)">
                <rect width="470" height="45" rx="4" fill="#1C2132" stroke="#475569" strokeWidth="0.5" />
                <text x="15" y="27" fill="#ECEFF1" fontSize="11" fontFamily="monospace">
                  qdrant (:6333) <tspan fill="#4FC3F7">● RUNNING</tspan>
                </text>
              </g>

              {/* mcp-server */}
              <g transform="translate(20, 85)">
                <rect width="470" height="45" rx="4" fill="#1C2132" stroke="#475569" strokeWidth="0.5" />
                <text x="15" y="27" fill="#ECEFF1" fontSize="11" fontFamily="monospace">
                  mcp-server (FastMCP · :8001) <tspan fill="#4FC3F7">● STANDBY</tspan>
                </text>
              </g>

              {/* orchestrator */}
              <g transform="translate(515, 85)">
                <rect width="470" height="45" rx="4" fill="#1C2132" stroke="#475569" strokeWidth="0.5" />
                <text x="15" y="27" fill="#ECEFF1" fontSize="11" fontFamily="monospace">
                  orchestrator (TypeScript · demo runner) <tspan fill="#81C784">● READY</tspan>
                </text>
              </g>
            </g>

            {/* Right Panel: Governance & Ledger */}
            <g transform="translate(1220, 1400)">
              <rect width="1050" height="150" rx="8" fill="#111520" stroke="#475569" strokeWidth="1" />
              <text x="20" y="-6" fill="#94A3B8" fontSize="11" fontFamily="sans-serif" fontWeight="bold">Governance & Ledger</text>

              {/* 4 Items */}
              {/* hr_policies */}
              <g transform="translate(20, 25)">
                <rect width="490" height="45" rx="4" fill="#1C2132" stroke="#475569" strokeWidth="0.5" />
                <text x="15" y="27" fill="#CFD8DC" fontSize="10.5" fontFamily="monospace">
                  📜 .governance/hr_policies.md — tiers · infractions · evolution
                </text>
              </g>

              {/* history.json */}
              <g transform="translate(530, 25)">
                <rect width="490" height="45" rx="4" fill="#1C2132" stroke="#475569" strokeWidth="0.5" />
                <text x="15" y="27" fill="#CFD8DC" fontSize="10.5" fontFamily="monospace">
                  📋 project_ledger/history.json — append-only event log
                </text>
              </g>

              {/* hooks_audit.log */}
              <g transform="translate(20, 85)">
                <rect width="490" height="45" rx="4" fill="#1C2132" stroke="#475569" strokeWidth="0.5" />
                <text x="15" y="27" fill="#CFD8DC" fontSize="10.5" fontFamily="monospace">
                  🔍 project_ledger/hooks_audit.log — per-turn trail
                </text>
              </g>

              {/* Evolution states */}
              <g transform="translate(530, 85)">
                <rect width="490" height="45" rx="4" fill="#1C2132" stroke="#475569" strokeWidth="0.5" />
                <text x="15" y="27" fill="#CFD8DC" fontSize="11" fontFamily="monospace">
                  Evolution states: <tspan fill="#81C784" fontWeight="bold">Stable</tspan> → <tspan fill="#FFE082">Mutating</tspan> → <tspan fill="#E57373">Degraded</tspan>
                </text>
              </g>
            </g>

          </g>
        </svg>
      </div>

      {/* Floating Canvas Guide */}
      <div className="absolute bottom-4 left-4 z-10 flex flex-col gap-1.5 p-3 rounded bg-[#121622]/95 border border-slate-800 text-[10px] text-slate-400 font-mono max-w-[280px] shadow-lg">
        <div className="flex items-center gap-1.5 font-bold text-slate-200 border-b border-slate-800 pb-1 mb-1 uppercase tracking-wide">
          <HelpCircle className="w-3.5 h-3.5 text-[#4FC3F7]" />
          Visual Guide Keys
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#4FC3F7]" />
          <span>Electric Blue: Orchestrator Core</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#CE93D8]" />
          <span>Purple: Contextual Memory Servers</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#4DB6AC]" />
          <span>Teal: Quality Gate Verifications</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#81C784]" />
          <span>Green/Gold: Tier Specialist Operators</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#FF9800]" />
          <span>Orange: Isolated Commit Flow Checks</span>
        </div>
      </div>
    </div>
  );
}
