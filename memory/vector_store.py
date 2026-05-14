"""
memory/vector_store.py — Módulo de Memória Vetorial Soberana
Projeto: RubberDuckFactory
Arquitetura: ChromaDB Embedded + sentence-transformers (all-MiniLM-L6-v2)
Uso: uv run python memory/vector_store.py
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ─── Configuração de Persistência ────────────────────────────────────────────
MEMORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory", "chroma_db")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ─── Agentes válidos do Squad ─────────────────────────────────────────────────
VALID_AGENTS = {"nova", "falcon", "shadow"}


class AgentMemory:
    """
    Interface de memória vetorial por agente.
    Cada agente possui sua própria coleção isolada no ChromaDB.
    """

    def __init__(self, persist_dir: str = MEMORY_DIR):
        os.makedirs(persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._model = SentenceTransformer(EMBEDDING_MODEL)
        self._collections: dict = {}

    def _get_collection(self, agent_id: str):
        """Retorna (ou cria) a coleção ChromaDB do agente."""
        agent_id = agent_id.lower()
        if agent_id not in VALID_AGENTS:
            raise ValueError(f"Agente '{agent_id}' não reconhecido. Válidos: {VALID_AGENTS}")
        if agent_id not in self._collections:
            self._collections[agent_id] = self._client.get_or_create_collection(
                name=f"{agent_id}_memory",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[agent_id]

    def remember(
        self,
        agent_id: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Grava um fragmento de memória para o agente.

        Args:
            agent_id: Nome do agente (nova, falcon, shadow)
            content:  Texto a ser embedado e armazenado
            metadata: Dicionário opcional com contexto adicional

        Returns:
            ID único da memória gravada
        """
        collection = self._get_collection(agent_id)
        memory_id = str(uuid.uuid4())
        embedding = self._model.encode(content).tolist()

        base_meta = {
            "agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            base_meta.update(metadata)

        collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[base_meta],
        )
        return memory_id

    def recall(
        self,
        agent_id: str,
        query: str,
        n_results: int = 5,
    ) -> list[dict]:
        """
        Busca semântica nas memórias do agente.

        Args:
            agent_id:  Nome do agente
            query:     Texto de consulta
            n_results: Número máximo de resultados

        Returns:
            Lista de dicts com 'content', 'metadata' e 'distance'
        """
        collection = self._get_collection(agent_id)
        count = collection.count()
        if count == 0:
            return []

        query_embedding = self._model.encode(query).tolist()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, count),
            include=["documents", "metadatas", "distances"],
        )

        memories = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            memories.append({"content": doc, "metadata": meta, "distance": dist})
        return memories

    def forget(self, agent_id: str, memory_id: str) -> bool:
        """
        Remove uma memória específica pelo ID.

        Args:
            agent_id:  Nome do agente
            memory_id: UUID da memória a remover

        Returns:
            True se removida com sucesso
        """
        collection = self._get_collection(agent_id)
        collection.delete(ids=[memory_id])
        return True

    def count(self, agent_id: str) -> int:
        """Retorna o número de memórias armazenadas para o agente."""
        return self._get_collection(agent_id).count()

    def status(self) -> dict:
        """Retorna um resumo do estado da memória de todos os agentes."""
        return {
            agent: self._get_collection(agent).count()
            for agent in VALID_AGENTS
        }


# ─── Smoke Test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🧠 Iniciando teste de memória vetorial...\n")

    mem = AgentMemory()

    # Grava memórias de teste
    id1 = mem.remember(
        "nova",
        "O projeto usa Next.js 15 com App Router e TypeScript estrito.",
        {"tipo": "arquitetura", "projeto": "board"},
    )
    id2 = mem.remember(
        "nova",
        "ChromaDB foi escolhido como banco vetorial por ser embedded e sem Docker.",
        {"tipo": "decisao_tecnica"},
    )
    mem.remember(
        "falcon",
        "O sovereign_proxy.py usa deepseek/deepseek-chat via OpenRouter.",
        {"tipo": "integracao"},
    )

    print(f"✅ Memórias gravadas. Status: {mem.status()}\n")

    # Busca semântica
    resultados = mem.recall("nova", "qual banco de dados vetorial usamos?", n_results=2)
    print("🔍 Recall para Nova — query: 'qual banco de dados vetorial usamos?'")
    for r in resultados:
        print(f"  [{r['distance']:.4f}] {r['content'][:80]}...")

    print("\n✅ Teste concluído com sucesso!")
