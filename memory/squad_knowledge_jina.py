"""
memory/squad_knowledge_jina.py — Gravação de Conhecimento Técnico: Jina AI
Projeto: RubberDuckFactory
Fonte: https://jina.ai/news/jina-embeddings-v4-universal-embeddings-for-multimodal-multilingual-retrieval/
Uso: uv run python memory/squad_knowledge_jina.py
"""

import os
import uuid
from datetime import datetime, timezone

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ─── Configuração ─────────────────────────────────────────────────────────────
MEMORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory", "chroma_db")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "squad_knowledge"

# ─── Resumo extraído pelo PO via curl/Jina Reader ─────────────────────────────
JINA_AI_KNOWLEDGE = [
    {
        "id": str(uuid.uuid4()),
        "content": (
            "Jina AI é uma empresa de infraestrutura de busca (Search Foundation) que desenvolve "
            "modelos de embedding, reranking e leitura de conteúdo web. Seu slogan é "
            "'Your Search Foundation, Supercharged.' e é parceira da Elastic."
        ),
        "metadata": {
            "topic": "jina_ai_overview",
            "source": "https://jina.ai/",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    },
    {
        "id": str(uuid.uuid4()),
        "content": (
            "jina-embeddings-v4 é um modelo de embedding universal com 3.8 bilhões de parâmetros "
            "que unifica representações de texto e imagem em um único pathway. Usa o backbone "
            "Qwen2.5-VL-3B-Instruct e elimina o 'modality gap' presente em arquiteturas dual-encoder "
            "como CLIP. Suporta embeddings single-vector (2048 dims) e multi-vector (128 dims/token "
            "para late interaction). Alcança 0.71 de alinhamento cross-modal vs 0.15 do OpenAI CLIP."
        ),
        "metadata": {
            "topic": "jina_embeddings_v4",
            "source": "https://jina.ai/news/jina-embeddings-v4-universal-embeddings-for-multimodal-multilingual-retrieval/",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    },
    {
        "id": str(uuid.uuid4()),
        "content": (
            "jina-embeddings-v4 usa LoRA adapters task-específicos (60M params cada) para três tarefas: "
            "asymmetric retrieval, symmetric similarity e code retrieval. Suporta até 32.768 tokens, "
            "29+ idiomas, imagens de até 20 megapixels. Supera OpenAI text-embedding-3-large em 12% "
            "em retrieval multilingual (66.49 vs 59.27) e em 28% em documentos longos (67.11 vs 52.42)."
        ),
        "metadata": {
            "topic": "jina_embeddings_v4_performance",
            "source": "https://jina.ai/news/jina-embeddings-v4-universal-embeddings-for-multimodal-multilingual-retrieval/",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    },
    {
        "id": str(uuid.uuid4()),
        "content": (
            "A arquitetura do jina-embeddings-v4 usa M-RoPE (Multimodal Rotary Position Embedding) "
            "e FlashAttention2. Imagens são convertidas em sequências de tokens e processadas junto "
            "com texto pelo decoder LLM, eliminando o gap de modalidade. Atinge 90.17 nDCG@5 no "
            "benchmark ViDoRe e 84.11 no Jina-VDR para recuperação de documentos visuais ricos "
            "(tabelas, gráficos, diagramas, screenshots)."
        ),
        "metadata": {
            "topic": "jina_embeddings_v4_architecture",
            "source": "https://arxiv.org/abs/2506.18902",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    },
    {
        "id": str(uuid.uuid4()),
        "content": (
            "Jina AI oferece uma suite completa de APIs para busca: Reader (converte URLs em Markdown "
            "para grounding de LLMs), Embeddings (multimodal multilingual), Reranker (maximiza "
            "relevância de busca) e Elastic Inference Service (modelos Jina nativos no Elasticsearch). "
            "Também disponibiliza MCP server, CLI e integração com HuggingFace. Modelos são open-source."
        ),
        "metadata": {
            "topic": "jina_ai_products",
            "source": "https://jina.ai/",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    },
    {
        "id": str(uuid.uuid4()),
        "content": (
            "jina-reranker-m0 é o reranker multimodal da Jina AI, compartilhando a mesma filosofia "
            "do jina-embeddings-v4: usa LLM como backbone (decoder-only) em vez de encoder-only, "
            "permitindo representação verdadeiramente multimodal. Junto com o v4, representa a visão "
            "da Jina AI de um 'search foundation model' unificado onde embedding e reranking emergem "
            "do mesmo modelo base."
        ),
        "metadata": {
            "topic": "jina_reranker_m0",
            "source": "https://jina.ai/news/jina-embeddings-v4-universal-embeddings-for-multimodal-multilingual-retrieval/",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    },
]


def main():
    print("🧠 Iniciando gravação de conhecimento sobre Jina AI na squad_knowledge...\n")

    # Inicializa ChromaDB
    os.makedirs(MEMORY_DIR, exist_ok=True)
    client = chromadb.PersistentClient(
        path=MEMORY_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    model = SentenceTransformer(EMBEDDING_MODEL)

    # Cria ou obtém a coleção squad_knowledge
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    print(f"📦 Coleção '{COLLECTION_NAME}' — documentos antes: {collection.count()}")

    # Grava cada fragmento de conhecimento
    for item in JINA_AI_KNOWLEDGE:
        embedding = model.encode(item["content"]).tolist()
        collection.add(
            ids=[item["id"]],
            embeddings=[embedding],
            documents=[item["content"]],
            metadatas=[item["metadata"]],
        )
        print(f"  ✅ Gravado: [{item['metadata']['topic']}]")

    print(f"\n📦 Coleção '{COLLECTION_NAME}' — documentos após: {collection.count()}")

    # ─── RECALL: Busca vetorial para validar ──────────────────────────────────
    print("\n" + "=" * 60)
    print("🔍 RECALL — Query: 'O que é o Jina AI e como funciona a busca multimodal?'")
    print("=" * 60)

    query = "O que é o Jina AI e como funciona a busca multimodal?"
    query_embedding = model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3,
        include=["documents", "metadatas", "distances"],
    )

    for i, (doc, meta, dist) in enumerate(
        zip(results["documents"][0], results["metadatas"][0], results["distances"][0])
    ):
        print(f"\n[{i+1}] Similaridade: {1 - dist:.4f} | Tópico: {meta['topic']}")
        print(f"    {doc[:200]}...")

    print("\n" + "=" * 60)
    print("🔍 RECALL — Query: 'jina-embeddings-v4 arquitetura e performance'")
    print("=" * 60)

    query2 = "jina-embeddings-v4 arquitetura e performance"
    query_embedding2 = model.encode(query2).tolist()

    results2 = collection.query(
        query_embeddings=[query_embedding2],
        n_results=3,
        include=["documents", "metadatas", "distances"],
    )

    for i, (doc, meta, dist) in enumerate(
        zip(results2["documents"][0], results2["metadatas"][0], results2["distances"][0])
    ):
        print(f"\n[{i+1}] Similaridade: {1 - dist:.4f} | Tópico: {meta['topic']}")
        print(f"    {doc[:200]}...")

    print("\n✅ Missão concluída! Conhecimento sobre Jina AI gravado e validado na squad_knowledge.")


if __name__ == "__main__":
    main()
