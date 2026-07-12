import fs from "fs";
import path from "path";
import AgentCard from "../components/AgentCard";

// Sem isto o Next pre-renderiza a pagina NO BUILD (dentro do container, sem os
// volumes montados) e o board serve HTML estatico vazio para sempre.
export const dynamic = "force-dynamic";

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

function readAllLogs(): any[] {
  const ledgerPath = path.resolve(process.cwd(), "..", "project_ledger", "history.json");
  if (!fs.existsSync(ledgerPath)) return [];
  try {
    const data = JSON.parse(fs.readFileSync(ledgerPath, "utf-8"));
    return data.logs || [];
  } catch (e) {
    console.error("[BOARD] Failed to read ledger:", e);
    return [];
  }
}

async function getRecentLogs(): Promise<any[]> {
  return readAllLogs().slice(-5).reverse();
}

type ModelCost = { model: string; calls: number; tokens: number; costUsd: number };
type Telemetry = {
  totalCostUsd: number;
  models: ModelCost[];
  duels: number;
  infraFailures: number;
  budgetBlocks: number;
  lastVerdict: { verdict: string; timestamp?: string; project?: string } | null;
};

async function getTelemetry(): Promise<Telemetry> {
  const logs = readAllLogs();
  const byModel = new Map<string, ModelCost>();
  let totalCostUsd = 0;
  let duels = 0;
  let infraFailures = 0;
  let budgetBlocks = 0;
  let lastVerdict: Telemetry["lastVerdict"] = null;

  const addCost = (model: string, tokens: number, costUsd: number) => {
    const entry = byModel.get(model) ?? { model, calls: 0, tokens: 0, costUsd: 0 };
    entry.calls += 1;
    entry.tokens += tokens;
    entry.costUsd += costUsd;
    byModel.set(model, entry);
    totalCostUsd += costUsd;
  };

  for (const log of logs) {
    switch (log.type) {
      case "COST_RECORD":
        addCost(log.model ?? "?", log.tokens?.total ?? 0, log.cost_usd ?? 0);
        break;
      case "DUEL_RUN":
        duels += 1;
        break;
      case "INFRA_FAILURE":
        infraFailures += 1;
        break;
      case "BUDGET_BLOCK":
        budgetBlocks += 1;
        break;
      case "DEPLOY_VERDICT":
        lastVerdict = { verdict: log.verdict, timestamp: log.timestamp, project: log.project };
        break;
    }
  }

  const models = [...byModel.values()].sort((a, b) => b.costUsd - a.costUsd).slice(0, 8);
  return { totalCostUsd, models, duels, infraFailures, budgetBlocks, lastVerdict };
}

function StatTile({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="rounded-xl border border-zinc-900 bg-zinc-900/20 p-4">
      <p className={`text-2xl font-bold ${accent ?? "text-zinc-100"}`}>{value}</p>
      <p className="mt-1 text-xs uppercase tracking-wider text-zinc-500">{label}</p>
    </div>
  );
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
  const [operationals, blacklisted, recentLogs, telemetry] = await Promise.all([
    getActiveAgents(),
    getBlacklistedAgents(),
    getRecentLogs(),
    getTelemetry(),
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

      {/* Telemetria — custo, duelos, infra, deploy */}
      <div className="mt-8 w-full max-w-4xl space-y-4">
        <HierarchyDivider label="Telemetria · Custo & Operações" />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatTile label="Custo total (LLM)" value={`$${telemetry.totalCostUsd.toFixed(4)}`} />
          <StatTile label="Duelos (ADR-003)" value={String(telemetry.duels)} />
          <StatTile
            label="Falhas de infra"
            value={String(telemetry.infraFailures)}
            accent={telemetry.infraFailures > 0 ? "text-amber-400" : undefined}
          />
          <StatTile
            label="Último deploy"
            value={telemetry.lastVerdict?.verdict ?? "—"}
            accent={
              telemetry.lastVerdict
                ? telemetry.lastVerdict.verdict === "GO"
                  ? "text-emerald-400"
                  : "text-red-400"
                : undefined
            }
          />
        </div>
        {telemetry.budgetBlocks > 0 && (
          <p className="text-left text-xs text-red-400/80">
            ⚠ {telemetry.budgetBlocks} chamada(s) bloqueada(s) por teto de orçamento
            (.governance/budget.json)
          </p>
        )}
        {telemetry.models.length > 0 && (
          <div className="rounded-xl border border-zinc-900 bg-zinc-900/20 p-4 text-left">
            <table className="w-full font-mono text-xs">
              <thead>
                <tr className="text-zinc-500">
                  <th className="pb-2 text-left font-normal uppercase tracking-wider">Modelo</th>
                  <th className="pb-2 text-right font-normal uppercase tracking-wider">Chamadas</th>
                  <th className="pb-2 text-right font-normal uppercase tracking-wider">Tokens</th>
                  <th className="pb-2 text-right font-normal uppercase tracking-wider">Custo</th>
                </tr>
              </thead>
              <tbody>
                {telemetry.models.map((m) => (
                  <tr key={m.model} className="border-t border-zinc-800/50 text-zinc-300">
                    <td className="py-1.5 pr-2">{m.model}</td>
                    <td className="py-1.5 text-right">{m.calls}</td>
                    <td className="py-1.5 text-right">{m.tokens.toLocaleString()}</td>
                    <td className="py-1.5 text-right">${m.costUsd.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

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
