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
import json
from datetime import datetime, timezone
from pathlib import Path
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
LEDGER_PATH = Path(__file__).parent / "project_ledger" / "history.json"

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
def remember(agent: str, content: str, metadata: dict | None = None, doc_id: str | None = None) -> dict:
    """
    Grava um fragmento de memória na coleção do agente.

    Args:
        agent:    Nome do agente (ex: 'nova', 'falcon', 'shadow').
        content:  Texto a ser memorizado.
        metadata: Dicionário opcional com metadados adicionais.
        doc_id:   ID único opcional (UUID) para evitar duplicações.

    Returns:
        dict com 'id' do ponto gravado e 'collection' utilizada.
    """
    collection = f"{agent.lower()}_memory"
    _ensure_collection(collection)

    vector = get_embedder().encode(content).tolist()
    if not doc_id:
        # ID determinístico por (agente, conteúdo): re-gravar faz upsert
        # em vez de duplicar. Evita memórias repetidas no recall.
        doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{agent.lower()}:{content}"))
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
    # qdrant-client >= 1.12 removeu .search(); usar query_points().points
    results = qdrant.query_points(
        collection_name=collection,
        query=vector,
        limit=top_k,
        with_payload=True,
    ).points
    seen: set[str] = set()
    out = []
    for r in results:
        content = r.payload.get("content", "")
        # Dedup defensivo: não devolve o mesmo conteúdo duas vezes
        if content in seen:
            continue
        seen.add(content)
        out.append({"id": str(r.id), "score": round(r.score, 4), "content": content})
    return out


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


@mcp.tool()
def cost_report(agent: str | None = None, period: str = "all") -> str:
    """
    Relatório de custo de tokens por agente.

    Args:
        agent:  Filtrar por nome de agente (opcional). None retorna todos.
        period: "today", "week", "month" ou "all" (padrão).

    Returns:
        Tabela Markdown com tokens e custo USD agregados por agente/modelo.
    """
    if not LEDGER_PATH.exists():
        return "Ledger não encontrado."

    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        ledger = json.load(f)

    now = datetime.now(timezone.utc)
    cutoffs = {"today": 1, "week": 7, "month": 30}
    cutoff_days = cutoffs.get(period)

    records = [e for e in ledger.get("logs", []) if e.get("type") == "COST_RECORD"]

    if cutoff_days:
        records = [
            r for r in records
            if (now - datetime.fromisoformat(r["timestamp"])).days < cutoff_days
        ]

    if agent:
        records = [r for r in records if r.get("agent", "").lower() == agent.lower()]

    if not records:
        return f"Nenhum registro de custo encontrado (agent={agent}, period={period})."

    # Agrega por agente + modelo
    agg: dict[str, dict] = {}
    for r in records:
        key = f"{r.get('agent', '?')}|{r.get('model', '?')}"
        if key not in agg:
            agg[key] = {"agent": r.get("agent", "?"), "model": r.get("model", "?"), "prompt": 0, "completion": 0, "cost": 0.0, "calls": 0}
        tokens = r.get("tokens", {})
        agg[key]["prompt"] += tokens.get("prompt", 0)
        agg[key]["completion"] += tokens.get("completion", 0)
        agg[key]["cost"] += r.get("cost_usd", 0.0)
        agg[key]["calls"] += 1

    lines = [
        f"## Relatório de Custo — period: {period}",
        "",
        "| Agente | Modelo | Chamadas | Tokens In | Tokens Out | Total | Custo USD |",
        "|---|---|---|---|---|---|---|",
    ]
    total_cost = 0.0
    for v in sorted(agg.values(), key=lambda x: x["cost"], reverse=True):
        total = v["prompt"] + v["completion"]
        lines.append(
            f"| {v['agent']} | {v['model']} | {v['calls']} "
            f"| {v['prompt']:,} | {v['completion']:,} | {total:,} | ${v['cost']:.6f} |"
        )
        total_cost += v["cost"]

    lines += ["", f"**Total: ${total_cost:.6f} USD** — {len(records)} interações"]
    return "\n".join(lines)


# ─── API REST Auxiliar para o Runner ─────────────────────────────────────────

def _get_semantic_cache(agent: str, task: str) -> str | None:
    collection = "semantic_cache"
    _ensure_collection(collection)
    
    info = qdrant.get_collection(collection_name=collection)
    if info.points_count == 0:
        return None
        
    vector = get_embedder().encode(task).tolist()
    
    results = qdrant.query_points(
        collection_name=collection,
        query=vector,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="agent",
                    match=MatchValue(value=agent)
                )
            ]
        ),
        limit=1,
        with_payload=True
    ).points

    if results:
        r = results[0]
        # Score de cosseno no Qdrant: >= 0.92 indica tarefa idêntica
        if r.score >= 0.92:
            return r.payload.get("content")
    return None


def _set_semantic_cache(agent: str, task: str, response: str, project: str) -> dict:
    collection = "semantic_cache"
    _ensure_collection(collection)
    
    vector = get_embedder().encode(task).tolist()
    doc_id = str(uuid.uuid4())
    
    payload = {
        "content": response,
        "agent": agent,
        "task": task,
        "project": project,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    qdrant.upsert(
        collection_name=collection,
        points=[PointStruct(id=doc_id, vector=vector, payload=payload)]
    )
    return {"id": doc_id, "collection": collection}


# Starlette endpoints
from starlette.responses import JSONResponse

async def api_remember(request):
    try:
        data = await request.json()
        agent = data.get("agent")
        content = data.get("content")
        metadata = data.get("metadata")
        doc_id = data.get("id")
        
        if not agent or not content:
            return JSONResponse({"error": "Campos 'agent' e 'content' são obrigatórios."}, status_code=400)
            
        res = remember(agent, content, metadata, doc_id)
        return JSONResponse(res)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_recall(request):
    try:
        data = await request.json()
        agent = data.get("agent")
        query = data.get("query")
        top_k = data.get("top_k", 5)
        
        if not agent or not query:
            return JSONResponse({"error": "Campos 'agent' e 'query' são obrigatórios."}, status_code=400)
            
        res = recall(agent, query, top_k)
        return JSONResponse(res)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_cache_get(request):
    try:
        data = await request.json()
        agent = data.get("agent")
        task = data.get("task")
        
        if not agent or not task:
            return JSONResponse({"error": "Campos 'agent' e 'task' são obrigatórios."}, status_code=400)
            
        cached_content = _get_semantic_cache(agent, task)
        return JSONResponse({"cached": cached_content is not None, "content": cached_content})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_cache_set(request):
    try:
        data = await request.json()
        agent = data.get("agent")
        task = data.get("task")
        response = data.get("response")
        project = data.get("project", "RubberDuckFactory")
        
        if not agent or not task or not response:
            return JSONResponse({"error": "Campos 'agent', 'task' e 'response' são obrigatórios."}, status_code=400)
            
        res = _set_semantic_cache(agent, task, response, project)
        return JSONResponse(res)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


def setup_api_routes(app):
    from starlette.routing import Route
    app.routes.append(Route("/api/remember", api_remember, methods=["POST"]))
    app.routes.append(Route("/api/recall", api_recall, methods=["POST"]))
    app.routes.append(Route("/api/semantic_cache/get", api_cache_get, methods=["POST"]))
    app.routes.append(Route("/api/semantic_cache/set", api_cache_set, methods=["POST"]))


# ─── Entrypoint ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        import uvicorn
        port = int(os.environ.get("MCP_PORT", 8001))
        # 0.0.0.0 para ser alcançável pelo mapeamento de porta do Docker.
        # 127.0.0.1 só escuta no loopback interno do container (inacessível de fora).
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        app = mcp.streamable_http_app()
        setup_api_routes(app)
        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run()