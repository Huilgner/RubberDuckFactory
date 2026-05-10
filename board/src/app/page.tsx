import fs from "fs";
import path from "path";
import AgentCard from "@/components/AgentCard";

type AgentData = {
  name: string;
  tier: number | string;
  status: string;
  points: number;
};

async function getActiveAgents(): Promise<AgentData[]> {
  const dir = path.join(process.cwd(), "..", "agents", "active");
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".json"));
  return files.map((file) => {
    const raw = JSON.parse(fs.readFileSync(path.join(dir, file), "utf-8"));
    return {
      name: raw.nome,
      tier: raw.tier,
      status: raw.status,
      points: (raw.pontos?.externos ?? 0) + (raw.pontos?.internos ?? 0),
    };
  });
}

const LEVEL_0: AgentData[] = [
  { name: "Usuário", tier: "supremo", status: "active", points: 0 },
];

const LEVEL_1: AgentData[] = [
  { name: "Sovereign-PO",     tier: "master", status: "active", points: 0 },
  { name: "Arquiteto Sênior", tier: "master", status: "active", points: 0 },
];

function HierarchyDivider({ label }: { label: string }) {
  return (
    <div className="flex w-full max-w-4xl items-center gap-4">
      <div className="h-px flex-1 bg-zinc-800" />
      <span className="text-xs font-semibold uppercase tracking-widest text-zinc-500">
        {label}
      </span>
      <div className="h-px flex-1 bg-zinc-800" />
    </div>
  );
}

export default async function Home() {
  const operationals = await getActiveAgents();

  return (
    <main className="flex min-h-screen flex-col items-center gap-8 bg-zinc-950 px-8 py-16">
      <h1 className="text-4xl font-bold tracking-tight text-zinc-50">
        RubberDuckFactory — Command Center
      </h1>

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
      <div className="grid w-full max-w-4xl grid-cols-1 gap-6 sm:grid-cols-3">
        {operationals.map((agent) => (
          <AgentCard key={agent.name} {...agent} />
        ))}
      </div>
    </main>
  );
}
