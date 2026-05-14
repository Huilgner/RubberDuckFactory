import fs from "fs";
import path from "path";
import AgentCard from "../components/AgentCard";

type AgentData = {
  name: string;
  tier: number | string;
  status: string;
  points: number;
  specialty?: string;
  model?: string;
  ruleset_version?: string;
  evolution?: string;
  success_rate?: number;
};

function readAgentsFromDir(dir: string): AgentData[] {
  if (!fs.existsSync(dir)) return [];
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".json"));
  const agents: AgentData[] = [];
  
  for (const file of files) {
    try {
      const raw = JSON.parse(fs.readFileSync(path.join(dir, file), "utf-8"));
      agents.push({
        name:      raw.nome,
        tier:      raw.tier,
        status:    raw.status,
        specialty:       raw.specialty,
        model:           raw.model,
        ruleset_version: raw.ruleset_version,
        evolution:       raw.evolution,
        success_rate:    raw.success_rate,
        points:    (raw.pontos?.externos ?? 0) + (raw.pontos?.internos ?? 0),
      });
    } catch (e) {
      console.error(`[BOARD] Failed to parse agent file ${file}:`, e);
    }
  }
  return agents;
}

async function getActiveAgents(): Promise<AgentData[]> {
  const agentsDir = path.resolve(process.cwd(), "..", "agents", "active");
  return readAgentsFromDir(agentsDir);
}

async function getBlacklistedAgents(): Promise<AgentData[]> {
  const agentsDir = path.resolve(process.cwd(), "..", "agents", "blacklist");
  return readAgentsFromDir(agentsDir);
}

async function getRecentLogs(): Promise<any[]> {
  const ledgerPath = path.resolve(process.cwd(), "..", "project_ledger", "history.json");
  if (!fs.existsSync(ledgerPath)) return [];
  try {
    const data = JSON.parse(fs.readFileSync(ledgerPath, "utf-8"));
    return (data.logs || []).slice(-5).reverse();
  } catch (e) {
    console.error("[BOARD] Failed to read ledger:", e);
    return [];
  }
}

const LEVEL_0: AgentData[] = [
  { name: "Usuário", tier: "supremo", status: "active", points: 0 },
];

const LEVEL_1: AgentData[] = [
  { name: "Sovereign-PO",     tier: "master", status: "active", points: 0 },
  { name: "Arquiteto Sênior", tier: "master", status: "active", points: 0 },
];

function HierarchyDivider({ label, danger }: { label: string; danger?: boolean }) {
  return (
    <div className="flex w-full max-w-4xl items-center gap-4">
      <div className={`h-px flex-1 ${danger ? "bg-red-900/60" : "bg-zinc-800"}`} />
      <span className={`text-xs font-semibold uppercase tracking-widest ${danger ? "text-red-500/80" : "text-zinc-500"}`}>
        {label}
      </span>
      <div className={`h-px flex-1 ${danger ? "bg-red-900/60" : "bg-zinc-800"}`} />
    </div>
  );
}

export default async function Home() {
  const [operationals, blacklisted, recentLogs] = await Promise.all([
    getActiveAgents(),
    getBlacklistedAgents(),
    getRecentLogs(),
  ]);

  return (
    <main className="flex min-h-screen flex-col items-center gap-8 bg-zinc-950 px-8 py-16 text-center">
      <div className="flex flex-col items-center gap-2">
        <h1 className="text-4xl font-bold tracking-tight text-zinc-50">
          RubberDuckFactory — Command Center
        </h1>
        <p className="max-w-2xl text-zinc-400">
          Hierarchical AI Agent Governance for Aseptic High-Security Projects.
          Orchestrating specialized models to stabilize delivery and reduce human workload.
        </p>
      </div>

      {/* Level 0 — Comissão Técnica */}
      <HierarchyDivider label="Nível 0 · Comissão Técnica" />
      <div className="flex justify-center">
        <div className="w-64">
          <AgentCard {...LEVEL_0[0]} />
        </div>
      </div>

      {/* Level 1 — Diretoria */}
      <HierarchyDivider label="Nível 1 · Diretoria" />
      <div className="grid w-full max-w-2xl grid-cols-1 gap-6 sm:grid-cols-2">
        {LEVEL_1.map((agent) => (
          <AgentCard key={agent.name} {...agent} />
        ))}
      </div>

      {/* Level 2 — Operacionais */}
      <HierarchyDivider label="Nível 2 · Operacionais" />
      {operationals.length > 0 ? (
        <div className="grid w-full max-w-4xl grid-cols-1 gap-6 sm:grid-cols-3">
          {operationals.map((agent) => (
            <AgentCard key={agent.name} {...agent} />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-zinc-800 p-8 w-full max-w-4xl">
          <p className="text-zinc-500">Nenhum agente operacional detectado em /agents/active</p>
        </div>
      )}

      {/* Project Ledger — Recent Activity */}
      <div className="mt-8 w-full max-w-4xl space-y-4">
        <HierarchyDivider label="Project Ledger · Atividade Recente" />
        <div className="rounded-xl border border-zinc-900 bg-zinc-900/20 p-4 font-mono text-xs text-left">
          {recentLogs.length > 0 ? (
            recentLogs.map((log: any, i: number) => (
              <div key={i} className="mb-2 last:mb-0 border-b border-zinc-800/50 pb-2 last:border-0">
                <span className="text-zinc-600">[{log.timestamp?.split('T')[1]?.split('.')[0] || "??:??:??"}]</span>{" "}
                <span className="text-blue-400">[{log.type}]</span>{" "}
                <span className="text-zinc-300">
                  {log.agent ? `${log.agent}: ` : ""}{log.task || log.prompt || log.action || ""}
                </span>
              </div>
            ))
          ) : (
            <p className="text-zinc-500 italic">Nenhuma atividade registrada no ledger ainda.</p>
          )}
        </div>
      </div>

      {/* Blacklist — Área Restrita */}
      {blacklisted.length > 0 && (
        <>
          <div className="mt-8 w-full max-w-4xl border-t border-dashed border-red-900/40" />
          <HierarchyDivider label="Área Restrita · Blacklist (Parâmetros Banidos)" danger />
          <div className="grid w-full max-w-4xl grid-cols-1 gap-6 sm:grid-cols-3">
            {blacklisted.map((agent) => (
              <AgentCard key={agent.name} {...agent} />
            ))}
          </div>
        </>
      )}
    </main>
  );
}
