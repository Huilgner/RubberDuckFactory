"""
memory/consolidate_memory.py — Consolidação da Memória Vetorial por Agente
Projeto: RubberDuckFactory
Uso: uv run python memory/consolidate_memory.py

Garante que cada agente tenha exatamente UMA memória no ChromaDB:
  - remove duplicatas de conteúdo idêntico;
  - se houver vários conteúdos distintos, mescla-os num único fragmento.
Idempotente: rodar novamente não altera um store já consolidado.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from vector_store import AgentMemory, VALID_AGENTS


def consolidate() -> None:
    print("=" * 60)
    print("🧹 RubberDuckFactory — Consolidação de Memória (1 por agente)")
    print("=" * 60)

    mem = AgentMemory()

    for agent in sorted(VALID_AGENTS):
        col = mem._get_collection(agent)
        data = col.get(include=["documents", "metadatas"])
        ids = data["ids"]
        docs = data["documents"]
        metas = data["metadatas"] or [{} for _ in docs]

        if not docs:
            print(f"\n  • {agent:8s}: vazio — nada a consolidar.")
            continue

        # Conteúdos distintos, preservando a ordem de inserção
        seen: set[str] = set()
        distinct: list[tuple[str, dict]] = []
        for doc, meta in zip(docs, metas):
            if doc not in seen:
                seen.add(doc)
                distinct.append((doc, meta or {}))

        # Apaga tudo da coleção
        col.delete(ids=ids)

        if len(distinct) == 1:
            content, meta = distinct[0]
            extra = {
                k: v for k, v in meta.items() if k not in ("agent_id", "timestamp")
            }
        else:
            # Mescla múltiplos fragmentos distintos num único documento
            content = "\n".join(f"- {doc}" for doc, _ in distinct)
            extra = {"tipo": "consolidado", "fragmentos": len(distinct)}

        new_id = mem.remember(agent, content, extra)
        print(
            f"\n  • {agent:8s}: {len(docs)} memória(s) → 1 "
            f"(distintos={len(distinct)}) | id={new_id[:8]}…"
        )

    # Resumo final
    print("\n" + "-" * 60)
    status = mem.status()
    for agent in sorted(status):
        print(f"  📦 {agent.capitalize():8s} → {status[agent]} memória(s)")
    assert all(c <= 1 for c in status.values()), "❌ Algum agente ficou com >1 memória!"
    print("-" * 60)
    print("✅ Consolidação concluída — 1 memória por agente.")
    print("=" * 60)


if __name__ == "__main__":
    consolidate()
