"""
memory/memory_test.py — Script de Validação da Memória Vetorial Soberana
Projeto: RubberDuckFactory
Uso: uv run python memory/memory_test.py

Testa o ciclo completo: remember → recall → forget → status
"""

from vector_store import AgentMemory


def run_tests():
    print("=" * 60)
    print("🧠 RubberDuckFactory — Teste de Memória Vetorial")
    print("=" * 60)

    mem = AgentMemory()

    # ── Teste 1: Gravação de memórias ────────────────────────────
    print("\n[1/4] Gravando memórias de teste...")

    id_nova_1 = mem.remember(
        "nova",
        "O projeto usa Next.js 15 com App Router e TypeScript estrito.",
        {"tipo": "arquitetura", "projeto": "board"},
    )
    id_nova_2 = mem.remember(
        "nova",
        "ChromaDB foi escolhido como banco vetorial por ser embedded e sem Docker.",
        {"tipo": "decisao_tecnica"},
    )
    id_falcon = mem.remember(
        "falcon",
        "O sovereign_proxy.py usa deepseek/deepseek-chat via OpenRouter.",
        {"tipo": "integracao"},
    )
    id_shadow = mem.remember(
        "shadow",
        "Shadow monitora conformidade com hr_policies.md e audita o history_log.json.",
        {"tipo": "governanca"},
    )

    print(f"  ✅ Nova    → {id_nova_1[:8]}... | {id_nova_2[:8]}...")
    print(f"  ✅ Falcon  → {id_falcon[:8]}...")
    print(f"  ✅ Shadow  → {id_shadow[:8]}...")

    # ── Teste 2: Status geral ─────────────────────────────────────
    print("\n[2/4] Status da memória por agente:")
    status = mem.status()
    for agent, count in status.items():
        print(f"  📦 {agent.capitalize():8s} → {count} memória(s)")

    # ── Teste 3: Busca semântica (recall) ─────────────────────────
    print("\n[3/4] Busca semântica (recall)...")

    queries = [
        ("nova",   "qual banco de dados vetorial usamos?"),
        ("falcon", "qual modelo de IA está integrado?"),
        ("shadow", "como funciona a auditoria de governança?"),
    ]

    for agent, query in queries:
        results = mem.recall(agent, query, n_results=2)
        print(f"\n  🔍 [{agent.upper()}] query: '{query}'")
        if results:
            for r in results:
                print(f"     [{r['distance']:.4f}] {r['content'][:75]}...")
        else:
            print("     ⚠️  Nenhum resultado encontrado.")

    # ── Teste 4: Remoção (forget) ─────────────────────────────────
    print("\n[4/4] Testando remoção de memória (forget)...")
    before = mem.count("nova")
    mem.forget("nova", id_nova_1)
    after = mem.count("nova")
    assert after == before - 1, "❌ Falha: contagem não decrementou após forget!"
    print(f"  ✅ Nova: {before} → {after} memória(s) após forget.")

    # ── Resultado Final ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("✅ TODOS OS TESTES PASSARAM — Memória Vetorial Operacional!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
