"""
agents/pleno_rag_worker.py — Agente Operário RAG (Retrieval-Augmented Generation)
Projeto: RubberDuckFactory
Fluxo: Pergunta → ChromaDB (squad_knowledge) → DeepSeek-V3 via OpenRouter → Resposta
Uso: uv run python agents/pleno_rag_worker.py "Sua pergunta aqui"
     uv run python agents/pleno_rag_worker.py  (modo interativo)
"""

# ─── CPU Fallback: força CPU para evitar erro com GTX 1050 (CC 6.1) ──────────
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import sys
import json
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import httpx
from dotenv import load_dotenv

# ─── Configuração ─────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.parent
MEMORY_DIR = str(ROOT_DIR / "memory" / "chroma_db")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "squad_knowledge"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL = "deepseek/deepseek-chat"
N_RESULTS = 3  # fragmentos recuperados do ChromaDB

load_dotenv(ROOT_DIR / ".env")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def retrieve(query: str, n_results: int = N_RESULTS) -> list[dict]:
    """Passo A — Retrieval: busca semântica na squad_knowledge."""
    client = chromadb.PersistentClient(
        path=MEMORY_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    count = collection.count()
    if count == 0:
        print("⚠️  Coleção 'squad_knowledge' está vazia. Execute memory/squad_knowledge_jina.py primeiro.")
        return []

    model = SentenceTransformer(EMBEDDING_MODEL)
    query_embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, count),
        include=["documents", "metadatas", "distances"],
    )

    fragments = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        fragments.append({
            "content": doc,
            "topic": meta.get("topic", "unknown"),
            "source": meta.get("source", ""),
            "similarity": round(1 - dist, 4),
        })
    return fragments


def generate(question: str, fragments: list[dict]) -> str:
    """Passo B — Generation: monta prompt RAG e chama DeepSeek-V3 via OpenRouter."""
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY não encontrada no .env")

    # Monta o contexto com os fragmentos recuperados
    context_parts = []
    for i, frag in enumerate(fragments, 1):
        context_parts.append(
            f"[Fragmento {i} | Tópico: {frag['topic']} | Similaridade: {frag['similarity']}]\n"
            f"{frag['content']}"
        )
    context = "\n\n".join(context_parts)

    system_prompt = (
        "Você é o Arquiteto Sênior do projeto RubberDuckFactory, especialista em arquitetura de busca "
        "e sistemas de IA. Responda com precisão técnica em português brasileiro, baseando-se "
        "EXCLUSIVAMENTE nos fragmentos de contexto fornecidos. Se o contexto não for suficiente, "
        "diga explicitamente o que está faltando."
    )

    user_prompt = (
        f"## Contexto Recuperado da Memória Vetorial (squad_knowledge)\n\n"
        f"{context}\n\n"
        f"---\n\n"
        f"## Pergunta\n\n"
        f"{question}"
    )

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/Huilgner/RubberDuckFactory",
        "X-Title": "RubberDuckFactory RAG Worker",
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(OPENROUTER_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    return data["choices"][0]["message"]["content"]


def main():
    # Obtém a pergunta via argumento CLI ou input interativo
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        print("🤖 Pleno RAG Worker — RubberDuckFactory")
        print("Digite sua pergunta (ou CTRL+C para sair):\n")
        question = input("❓ Pergunta: ").strip()
        if not question:
            print("Nenhuma pergunta fornecida. Encerrando.")
            sys.exit(0)

    print(f"\n{'='*60}")
    print(f"❓ PERGUNTA: {question}")
    print(f"{'='*60}\n")

    # ── Passo A: Retrieval ────────────────────────────────────────────────────
    print("🔍 Passo A — Retrieval: buscando na squad_knowledge...")
    fragments = retrieve(question)

    if not fragments:
        print("❌ Nenhum fragmento recuperado. Encerrando.")
        sys.exit(1)

    print(f"  ✅ {len(fragments)} fragmento(s) recuperado(s):")
    for frag in fragments:
        print(f"     [{frag['similarity']:.4f}] {frag['topic']}")

    # ── Passo B: Generation ───────────────────────────────────────────────────
    print(f"\n🧠 Passo B — Generation: enviando para {LLM_MODEL} via OpenRouter...")
    answer = generate(question, fragments)

    print(f"\n{'='*60}")
    print("💬 RESPOSTA DO DEEPSEEK-V3:")
    print(f"{'='*60}\n")
    print(answer)
    print(f"\n{'='*60}")
    print("✅ RAG Worker concluído com sucesso.")


if __name__ == "__main__":
    main()
