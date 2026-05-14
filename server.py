"""
server.py — Servidor MCP da RubberDuckFactory
Expõe ferramentas de memória vetorial soberana via Qdrant para os agentes do Squad.

Ferramentas disponíveis:
  - remember(agent, content, metadata)  → grava fragmento na coleção do agente
  - recall(agent, query, top_k)         → busca semântica na memória do agente
  - forget(agent, doc_id)               → remove fragmento por ID
  - status(agent)                       → retorna contagem de fragmentos na coleção
"""

import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from sentence_transformers import SentenceTransformer
import uuid

# ─── Carregamento seguro de variáveis de ambiente ────────────────────────────
load_dotenv()

QDRANT_URL: str = os.environ["QDRANT_URL"]
QDRANT_API_KEY: str = os.environ["QDRANT_API_KEY"]

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
VECTOR_SIZE = 384  # dimensão do all-MiniLM-L6-v2

# ─── Clientes ────────────────────────────────────────────────────────────────
qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

_embedder_instance = None

def get_embedder():
    """Carrega o modelo pesado apenas na primeira vez que for chamado."""
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder_instance

# ─── Servidor MCP ────────────────────────────────────────────────────────────
mcp = FastMCP(
    name="RubberDuckFactory Memory",
    instructions="Memória vetorial soberana dos agentes do Squad via Qdrant.",
)


def _ensure_collection(collection_name: str) -> None:
    """Cria a coleção no Qdrant se ainda não existir."""
    existing = [c.name for c in qdrant.get_collections().collections]
    if collection_name not in existing:
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


# ─── Ferramentas MCP ─────────────────────────────────────────────────────────

@mcp.tool()
def remember(agent: str, content: str, metadata: dict | None = None) -> dict:
    """
    Grava um fragmento de memória na coleção do agente.

    Args:
        agent:    Nome do agente (ex: 'nova', 'falcon', 'shadow').
        content:  Texto a ser memorizado.
        metadata: Dicionário opcional com metadados adicionais.

    Returns:
        dict com 'id' do ponto gravado e 'collection' utilizada.
    """
    collection = f"{agent.lower()}_memory"
    _ensure_collection(collection)

    vector = get_embedder().encode(content).tolist()
    doc_id = str(uuid.uuid4())
    payload = {"content": content, "agent": agent}
    if metadata:
        payload.update(metadata)

    qdrant.upsert(
        collection_name=collection,
        points=[PointStruct(id=doc_id, vector=vector, payload=payload)],
    )
    return {"id": doc_id, "collection": collection}


@mcp.tool()
def recall(agent: str, query: str, top_k: int = 5) -> list[dict]:
    """
    Busca semântica na memória do agente.

    Args:
        agent:  Nome do agente.
        query:  Texto de consulta.
        top_k:  Número máximo de resultados (padrão: 5).

    Returns:
        Lista de dicts com 'id', 'score' e 'content'.
    """
    collection = f"{agent.lower()}_memory"
    _ensure_collection(collection)

    vector = get_embedder().encode(query).tolist()
    results = qdrant.search(
        collection_name=collection,
        query_vector=vector,
        limit=top_k,
        with_payload=True,
    )
    return [
        {
            "id": str(r.id),
            "score": round(r.score, 4),
            "content": r.payload.get("content", ""),
        }
        for r in results
    ]


@mcp.tool()
def forget(agent: str, doc_id: str) -> dict:
    """
    Remove um fragmento de memória pelo ID.

    Args:
        agent:   Nome do agente.
        doc_id:  UUID do ponto a ser removido.

    Returns:
        dict com 'deleted' (bool) e 'id'.
    """
    collection = f"{agent.lower()}_memory"
    try:
        qdrant.delete(
            collection_name=collection,
            points_selector=[doc_id],
        )
        return {"deleted": True, "id": doc_id}
    except Exception as e:
        return {"deleted": False, "id": doc_id, "error": str(e)}


@mcp.tool()
def status(agent: str) -> dict:
    """
    Retorna o status da coleção de memória do agente.

    Args:
        agent: Nome do agente.

    Returns:
        dict com 'collection', 'vectors_count' e 'status'.
    """
    collection = f"{agent.lower()}_memory"
    _ensure_collection(collection)

    info = qdrant.get_collection(collection_name=collection)
    return {
        "collection": collection,
        "vectors_count": info.points_count,  # <-- CORREÇÃO AQUI
        "status": str(info.status),
    }


# ─── Entrypoint ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
