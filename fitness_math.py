"""
fitness_math.py — Estatística de fitness do RubberDuckFactory (ADR-003).

Problema que este módulo resolve: média simples de success_rate amplifica sorte.
Um agente com 2 tarefas a 100% NÃO é mais apto que um com 200 tarefas a 95% —
mas é o que uma média ingênua conclui. Aqui usamos o limite inferior do
intervalo de Wilson: com poucas amostras o score é puxado para baixo,
e só converge para a taxa observada conforme a evidência acumula.

Usado por: agent_runner.py (evolução por janela) e gene_crossover.py (seleção de genes).
"""

# Amostras mínimas antes de qualquer decisão automática de fitness
MIN_SAMPLES_EVOLUTION = 5    # transição de estado evolutivo (Stable/Mutating/Degraded)
MIN_SAMPLES_GENE_POOL = 10   # elegibilidade de um gene (modelo/ruleset) no crossover

# Janela deslizante da evolução: só as últimas N tarefas contam para o estado
EVOLUTION_WINDOW = 20


def wilson_lower_bound(successes: int, total: int, z: float = 1.96) -> float:
    """
    Limite inferior do intervalo de confiança de Wilson (95% com z=1.96)
    para uma proporção de sucessos. Retorna valor em [0, 1].

    Propriedades desejáveis para seleção de genes:
      - total=0  -> 0.0 (nenhuma evidência = nenhuma confiança)
      - 2/2      -> ~0.34  (100% com n=2 vale pouco)
      - 190/200  -> ~0.91  (95% com n=200 vale muito)
    """
    if total <= 0:
        return 0.0
    successes = max(0, min(successes, total))
    p = successes / total
    z2 = z * z
    denom = 1.0 + z2 / total
    centre = p + z2 / (2.0 * total)
    margin = z * ((p * (1.0 - p) + z2 / (4.0 * total)) / total) ** 0.5
    return max(0.0, (centre - margin) / denom)


def fitness_score(successes: int, total: int) -> float:
    """Score de fitness em [0, 100] — Wilson lower bound em percentual."""
    return round(wilson_lower_bound(successes, total) * 100.0, 1)


def rolling_success_rate(recent_results: list[int]) -> float | None:
    """
    Taxa de sucesso da janela deslizante (recent_results: lista de 0/1,
    mais recente por último). None se não houver amostras suficientes
    para uma decisão de evolução.
    """
    window = recent_results[-EVOLUTION_WINDOW:]
    if len(window) < MIN_SAMPLES_EVOLUTION:
        return None
    return round(sum(window) / len(window) * 100.0, 1)
