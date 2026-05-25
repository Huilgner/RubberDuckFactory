import { useState, useEffect } from 'react';

export interface LiveAgent {
  nome: string;
  tier: number;
  model: string;
  evolution: 'Stable' | 'Mutating' | 'Degraded';
  pontos: { externos: number; internos: number };
  status: string;
}

// Mapeamento: node-id do diagrama → nome do arquivo JSON em agents/active/
const AGENT_MAP: Record<string, string> = {
  'agent-shadow':  'shadow',
  'agent-chen':    'chen',
  'agent-nova':    'nova',
  'agent-atlas':   'atlas',
  'agent-lens':    'lens',
  'agent-phoenix': 'phoenix',
  'agent-falcon':  'falcon',
  'agent-quill':   'quill',
};

export const EVOLUTION_COLOR: Record<string, string> = {
  Stable:   '#81C784',
  Mutating: '#FFE082',
  Degraded: '#E57373',
};

export function useAgentData(): {
  agents: Record<string, LiveAgent>;
  loading: boolean;
  isLive: boolean;
} {
  const [agents, setAgents] = useState<Record<string, LiveAgent>>({});
  const [loading, setLoading] = useState(true);
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    const entries = Object.entries(AGENT_MAP);

    Promise.allSettled(
      entries.map(([nodeId, filename]) =>
        fetch(`/agents/${filename}.json`, { cache: 'no-store' })
          .then(r => {
            if (!r.ok) throw new Error(`${r.status}`);
            return r.json();
          })
          .then((data: LiveAgent) => ({ nodeId, data }))
      )
    ).then(results => {
      const map: Record<string, LiveAgent> = {};
      let anySuccess = false;

      results.forEach(r => {
        if (r.status === 'fulfilled') {
          map[r.value.nodeId] = r.value.data;
          anySuccess = true;
        }
      });

      setAgents(map);
      setIsLive(anySuccess);
      setLoading(false);
    });
  }, []);

  return { agents, loading, isLive };
}
