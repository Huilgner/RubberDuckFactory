import AgentCard from "@/components/AgentCard";

const AGENTS = [
  { name: "Shadow", tier: 1, status: "active", points: 0 },
  { name: "Nova",   tier: 1, status: "active", points: 0 },
  { name: "Falcon", tier: 1, status: "active", points: 0 },
];

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center gap-12 bg-zinc-950 px-8 py-16">
      <h1 className="text-4xl font-bold tracking-tight text-zinc-50">
        RubberDuckFactory — Command Center
      </h1>

      <section className="grid w-full max-w-4xl grid-cols-1 gap-6 sm:grid-cols-3">
        {AGENTS.map((agent) => (
          <AgentCard key={agent.name} {...agent} />
        ))}
      </section>
    </main>
  );
}
