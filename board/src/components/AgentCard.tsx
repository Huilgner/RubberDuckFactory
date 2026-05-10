type AgentCardProps = {
  name: string;
  tier: number | string;
  status: string;
  points: number;
};

const tierStyles: Record<string, string> = {
  "1": "border-zinc-600 hover:border-zinc-400 hover:shadow-zinc-500/20",
  "2": "border-blue-600 hover:border-blue-400 hover:shadow-blue-500/30",
  "3": "border-purple-600 hover:border-purple-400 hover:shadow-purple-500/30",
  "4": "border-amber-500 hover:border-amber-300 hover:shadow-amber-400/40",
};

const tierLabel: Record<string, string> = {
  "1": "Observer",
  "2": "Operator",
  "3": "Specialist",
  "4": "Architect",
};

const statusConfig: Record<string, { dot: string; label: string }> = {
  active:    { dot: "bg-emerald-400 shadow-emerald-400/70", label: "Active" },
  suspended: { dot: "bg-red-500 shadow-red-500/70",         label: "Suspended" },
  blacklist: { dot: "bg-red-600 shadow-red-600/70",         label: "Blacklisted" },
  inactive:  { dot: "bg-zinc-500",                          label: "Inactive" },
};

export default function AgentCard({ name, tier, status, points }: AgentCardProps) {
  const tierKey = String(tier);
  const border = tierStyles[tierKey] ?? tierStyles["1"];
  const clearance = tierLabel[tierKey] ?? `Tier ${tier}`;
  const { dot, label } = statusConfig[status] ?? statusConfig["inactive"];

  return (
    <div
      className={`
        relative flex flex-col gap-4 rounded-2xl border bg-zinc-900 p-6
        shadow-lg transition-all duration-300 hover:shadow-xl
        ${border}
      `}
    >
      {/* tier badge */}
      <span className="absolute right-4 top-4 rounded-full bg-zinc-800 px-2 py-0.5 text-xs font-semibold uppercase tracking-widest text-zinc-400">
        T{tierKey} · {clearance}
      </span>

      {/* avatar placeholder */}
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-zinc-800 text-2xl font-bold text-zinc-300 ring-2 ring-zinc-700">
        {name[0].toUpperCase()}
      </div>

      {/* name */}
      <div>
        <p className="text-xs uppercase tracking-widest text-zinc-500">Agent ID</p>
        <h2 className="text-xl font-bold text-zinc-100">{name}</h2>
      </div>

      {/* points */}
      <div className="rounded-xl bg-zinc-800/60 px-4 py-3 text-center">
        <p className="text-xs uppercase tracking-widest text-zinc-500">Points</p>
        <p className="text-3xl font-extrabold tabular-nums text-zinc-100">{points}</p>
      </div>

      {/* status */}
      <div className="flex items-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full shadow-md ${dot}`} />
        <span className="text-sm font-medium text-zinc-300">{label}</span>
      </div>
    </div>
  );
}
