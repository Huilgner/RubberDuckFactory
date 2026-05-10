type AgentCardProps = {
  name: string;
  tier: number | string;
  status: string;
  points: number;
};

const tierStyles: Record<string, string> = {
  "1":     "border-zinc-600 hover:border-zinc-400 hover:shadow-zinc-500/20",
  "2":     "border-blue-600 hover:border-blue-400 hover:shadow-blue-500/30",
  "3":     "border-purple-600 hover:border-purple-400 hover:shadow-purple-500/30",
  "4":     "border-amber-500 hover:border-amber-300 hover:shadow-amber-400/40",
  master:  "border-fuchsia-500 hover:border-fuchsia-300 hover:shadow-fuchsia-500/40",
  supremo: "border-cyan-400 hover:border-cyan-200 hover:shadow-cyan-400/50",
};

const tierLabel: Record<string, string> = {
  "1":     "Observer",
  "2":     "Operator",
  "3":     "Specialist",
  "4":     "Architect",
  master:  "Master",
  supremo: "Supremo",
};

const statusConfig: Record<string, { dot: string; label: string }> = {
  active:    { dot: "bg-emerald-400 shadow-emerald-400/70", label: "Active" },
  suspended: { dot: "bg-red-500 shadow-red-500/70",         label: "Suspended" },
  blacklist: { dot: "bg-red-600 shadow-red-600/70",         label: "Blacklisted" },
  demitido:  { dot: "bg-red-700 shadow-red-700/60",         label: "Demitido" },
  inactive:  { dot: "bg-zinc-500",                          label: "Inactive" },
};

const INACTIVE_STATUSES = new Set(["demitido", "suspended", "blacklist", "inactive"]);

export default function AgentCard({ name, tier, status, points }: AgentCardProps) {
  const tierKey    = String(tier);
  const border     = tierStyles[tierKey] ?? tierStyles["1"];
  const clearance  = tierLabel[tierKey] ?? `Tier ${tier}`;
  const { dot, label } = statusConfig[status] ?? statusConfig["inactive"];
  const isDead     = INACTIVE_STATUSES.has(status);

  return (
    <div
      className={`
        relative flex flex-col gap-4 rounded-2xl border p-6
        shadow-lg transition-all duration-300
        ${isDead
          ? "border-red-900/50 bg-zinc-900/40 grayscale opacity-55 hover:opacity-70 hover:grayscale-0 hover:border-red-700/60"
          : `bg-zinc-900 hover:shadow-xl ${border}`
        }
      `}
    >
      {/* tier badge */}
      <span className="absolute right-4 top-4 rounded-full bg-zinc-800 px-2 py-0.5 text-xs font-semibold uppercase tracking-widest text-zinc-400">
        {isNaN(Number(tierKey)) ? clearance : `T${tierKey} · ${clearance}`}
      </span>

      {/* skull overlay for dead agents */}
      {isDead && (
        <span className="absolute left-4 top-4 text-lg select-none" aria-hidden>
          ☠
        </span>
      )}

      {/* avatar */}
      <div className={`
        flex h-14 w-14 items-center justify-center rounded-full text-2xl font-bold ring-2
        ${isDead
          ? "bg-red-950/40 text-red-400/60 ring-red-900/40"
          : "bg-zinc-800 text-zinc-300 ring-zinc-700"
        }
      `}>
        {name[0].toUpperCase()}
      </div>

      {/* name */}
      <div>
        <p className="text-xs uppercase tracking-widest text-zinc-500">Agent ID</p>
        <h2 className={`text-xl font-bold ${isDead ? "text-red-400/70 line-through" : "text-zinc-100"}`}>
          {name}
        </h2>
      </div>

      {/* points */}
      <div className={`rounded-xl px-4 py-3 text-center ${isDead ? "bg-red-950/20" : "bg-zinc-800/60"}`}>
        <p className="text-xs uppercase tracking-widest text-zinc-500">Points</p>
        <p className={`text-3xl font-extrabold tabular-nums ${isDead ? "text-red-500/50" : "text-zinc-100"}`}>
          {points}
        </p>
      </div>

      {/* status */}
      <div className="flex items-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full shadow-md ${dot}`} />
        <span className={`text-sm font-medium ${isDead ? "text-red-400/70" : "text-zinc-300"}`}>
          {label}
        </span>
      </div>
    </div>
  );
}
