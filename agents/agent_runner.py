#!/usr/bin/env python3
"""
agents/agent_runner.py -- Runner de Agentes do Squad RubberDuckFactory

Modos:
  1. Hello-world (sem args):
       uv run python agents/agent_runner.py
       -> testa todos os agentes ativos com mensagem de apresentacao

  2. Tarefa especifica:
       uv run python agents/agent_runner.py --agent chen --task "..." [--project "Nome"]
       -> delega briefing a um agente, atualiza ledger e stats automaticamente

Pos-tarefa (modo 2):
  - tasks_completed / tasks_failed e success_rate atualizados no JSON do agente
  - Transicao de evolucao aplicada automaticamente se success_rate cruzar threshold
  - Entrada TAREFA_OK / TAREFA_FALHA gravada em project_ledger/agent_ledger.log
  - Entrada TASK_SUCCESS / TASK_FAILURE gravada em project_ledger/history.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 stdout to avoid cp1252 encoding errors on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from cost_tracker import record_cost

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------

ROOT_DIR       = Path(__file__).parent.parent
AGENTS_DIR     = ROOT_DIR / "agents" / "active"
LEDGER_DIR     = ROOT_DIR / "project_ledger"
FILE_REGISTRY  = LEDGER_DIR / "file_registry.json"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

load_dotenv(ROOT_DIR / ".env")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

if not OPENROUTER_API_KEY:
    raise SystemExit(
        "OPENROUTER_API_KEY nao encontrada no .env\n"
        "Preencha o arquivo .env com: OPENROUTER_API_KEY=sk-or-v1-..."
    )

# Tokens maximos por modelo -- Gemini 2.5 Pro consome muitos tokens de raciocinio
MODEL_MAX_TOKENS: dict[str, int] = {
    "google/gemini-2.5-pro":           8000,
    "google/gemini-2.5-flash":         4000,
    "google/gemini-2.5-flash-lite":    2000,
    "deepseek/deepseek-chat":          4000,
    "deepseek/deepseek-v4-flash:free": 2000,
    "anthropic/claude-opus-4":         4000,
    "anthropic/claude-sonnet-4-5":     6000,
}
DEFAULT_MAX_TOKENS = 3000

TIER_NAMES = {1: "Observer", 2: "Operator", 3: "Specialist", 4: "Architect"}


# ---------------------------------------------------------------------------
# Carregamento de agentes
# ---------------------------------------------------------------------------

def load_agent(name: str) -> dict:
    """Carrega um agente pelo nome (case-insensitive). Levanta SystemExit se nao encontrado."""
    for path in AGENTS_DIR.glob("*.json"):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("nome", "").lower() == name.lower():
            d["_file"] = str(path)
            return d
    raise SystemExit(f"Agente '{name}' nao encontrado em {AGENTS_DIR}")


def load_all_agents() -> list[dict]:
    """Carrega todos os agentes ativos."""
    agents = []
    for path in sorted(AGENTS_DIR.glob("*.json")):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            d["_file"] = str(path)
            agents.append(d)
        except Exception:
            pass
    return agents


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

def build_system_prompt(agent: dict) -> str:
    """
    Gera system prompt a partir dos campos do JSON do agente.
    Aceita override completo via campo 'system_prompt' no JSON.
    """
    if "system_prompt" in agent:
        return agent["system_prompt"]

    nome      = agent.get("nome", "Agent")
    tier      = agent.get("tier", 1)
    specialty = agent.get("specialty", "General")
    model     = agent.get("model", "unknown")
    ruleset   = agent.get("ruleset_version", "v1")
    evolution = agent.get("evolution", "Stable")
    sr        = agent.get("success_rate", 100)
    tier_name = TIER_NAMES.get(tier, "Agent")

    return (
        f"You are {nome}, a Tier {tier} {tier_name} ({specialty}) "
        f"in the RubberDuckFactory AI agent squad.\n"
        f"Model: {model} | Ruleset: {ruleset} | Evolution: {evolution} | Success rate: {sr}%\n\n"
        "Operating principles:\n"
        "- Deliver precise, production-ready work within your specialty\n"
        "- Respond directly to the task -- no preamble, no filler\n"
        "- Be complete but concise; code must be correct and runnable\n"
        "- Flag ambiguities clearly rather than guessing\n"
        "- Follow existing patterns and conventions of the codebase\n\n"
        "You report to the Orchestrator (Claude). "
        "Your output will be reviewed before integration."
    )


# ---------------------------------------------------------------------------
# Chamada a API
# ---------------------------------------------------------------------------

def call_agent(agent: dict, user_message: str, max_tokens: int | None = None) -> dict:
    """
    Chama o agente via OpenRouter.
    Retorna: {content, finish_reason, prompt_tokens, completion_tokens, success, error}
    """
    model      = agent.get("model", "deepseek/deepseek-chat")
    system_msg = build_system_prompt(agent)

    if max_tokens is None:
        max_tokens = MODEL_MAX_TOKENS.get(model, DEFAULT_MAX_TOKENS)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://github.com/Huilgner/RubberDuckFactory",
        "X-Title":       "RubberDuckFactory",
    }
    payload = {
        "model":    model,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_message},
        ],
        "temperature": 0.3,
        "max_tokens":  max_tokens,
    }

    try:
        with httpx.Client(timeout=180.0) as client:
            resp = client.post(OPENROUTER_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data  = resp.json()
            usage = data.get("usage", {})
            return {
                "content":           (data["choices"][0]["message"]["content"] or "").strip(),
                "finish_reason":     data["choices"][0].get("finish_reason", "?"),
                "prompt_tokens":     usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "success":           True,
                "error":             None,
            }
    except httpx.HTTPStatusError as e:
        return {
            "content": "", "finish_reason": "error",
            "prompt_tokens": 0, "completion_tokens": 0,
            "success": False,
            "error": f"HTTP {e.response.status_code}: {e.response.text[:300]}",
        }
    except Exception as e:
        return {
            "content": "", "finish_reason": "error",
            "prompt_tokens": 0, "completion_tokens": 0,
            "success": False, "error": str(e),
        }


# ---------------------------------------------------------------------------
# Atualizacao de stats e evolucao do agente
# ---------------------------------------------------------------------------

def _compute_evolution(sr: float) -> str:
    if sr >= 85.0:
        return "Stable"
    elif sr >= 70.0:
        return "Mutating"
    return "Degraded"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_ledger(entry: dict) -> None:
    ledger = LEDGER_DIR / "agent_ledger.log"
    if not ledger.exists():
        return
    with open(ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def update_agent_stats(agent: dict, technical_success: bool) -> dict:
    """
    Incrementa tasks_completed ou tasks_failed, recalcula success_rate,
    aplica transicao de evolucao se necessario. Retorna o dict atualizado.
    """
    file_path = Path(agent["_file"])
    d = json.loads(file_path.read_text(encoding="utf-8"))

    if technical_success:
        d["tasks_completed"] = d.get("tasks_completed", 0) + 1
    else:
        d["tasks_failed"] = d.get("tasks_failed", 0) + 1

    total = d.get("tasks_completed", 0) + d.get("tasks_failed", 0)
    if total > 0:
        d["success_rate"] = round(d["tasks_completed"] / total * 100, 1)

    # Transicao de evolucao automatica
    new_evolution = _compute_evolution(float(d.get("success_rate", 100)))
    old_evolution = d.get("evolution", "Stable")
    if new_evolution != old_evolution:
        d["evolution"] = new_evolution
        _append_ledger({
            "ts":           _ts(),
            "type":         "EVOLUCAO",
            "agent":        d.get("nome", "?"),
            "from":         old_evolution,
            "to":           new_evolution,
            "success_rate": d.get("success_rate"),
            "trigger":      "agent_runner_pos_tarefa",
        })
        print(f"[EVOLUCAO] {d.get('nome','?')}: {old_evolution} -> {new_evolution} "
              f"(sr={d.get('success_rate')}%)")

    file_path.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    return d


# ---------------------------------------------------------------------------
# Ledger e historico
# ---------------------------------------------------------------------------

def write_task_ledger(agent: dict, success: bool, task: str, project: str,
                      error: str = "") -> None:
    """Escreve TAREFA_OK ou TAREFA_FALHA no agent_ledger.log."""
    _append_ledger({
        "ts":      _ts(),
        "type":    "TAREFA_OK" if success else "TAREFA_FALHA",
        "agent":   agent.get("nome", "?"),
        "project": project or "n/a",
        "reason":  task[:120] if success else (error or task[:120]),
    })


def write_history(agent: dict, success: bool, task: str, error: str = "") -> None:
    """Escreve TASK_SUCCESS ou TASK_FAILURE no history.json."""
    history_file = LEDGER_DIR / "history.json"
    try:
        data = json.loads(history_file.read_text(encoding="utf-8"))
        if "logs" not in data:
            data["logs"] = []
        entry: dict = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "type":      "TASK_SUCCESS" if success else "TASK_FAILURE",
            "agent":     agent.get("nome", "?"),
            "task":      task[:200],
        }
        if not success and error:
            entry["reason"] = error[:200]
        data["logs"].append(entry)
        history_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"  [WARNING] Nao foi possivel gravar em history.json: {e}")


# ---------------------------------------------------------------------------
# Modos de execucao
# ---------------------------------------------------------------------------

def run_hello_world() -> None:
    """Modo legado: testa todos os agentes com mensagem de apresentacao."""
    print("=" * 60)
    print("  AGENT RUNNER -- RubberDuckFactory Squad")
    print("  Testando: nome + modelo + hello world de cada agente")
    print("=" * 60)
    print()

    agents = load_all_agents()
    if not agents:
        print("Nenhum agente encontrado em agents/active/")
        return

    for agent in agents:
        nome      = agent.get("nome", "?")
        model     = agent.get("model", "?")
        tier      = agent.get("tier", "?")
        evolution = agent.get("evolution", "Stable")

        print(f"{'-' * 60}")
        print(f"Agente: {nome} | Tier {tier} | {evolution} | {model}")
        print()

        msg = (
            f"Apresente-se em uma unica mensagem curta: seu nome ({nome}), "
            f"seu modelo ({model}) e um 'Hello World'."
        )
        resultado = call_agent(agent, msg, max_tokens=1000)
        record_cost(
            agent=nome, model=model, task="hello_world",
            prompt_tokens=resultado["prompt_tokens"],
            completion_tokens=resultado["completion_tokens"],
        )

        if resultado["success"]:
            print(f"  {resultado['content']}")
        else:
            print(f"  ERRO: {resultado['error']}")
        print(f"  Tokens: {resultado['prompt_tokens']} in / {resultado['completion_tokens']} out")
        print()

    print("=" * 60)
    print("Todos os agentes responderam.")
    print("=" * 60)


# ---------------------------------------------------------------------------
# File registry — atualização de autoria por agente
# ---------------------------------------------------------------------------

def update_file_registry(files: list[str], agent: dict, project: str) -> None:
    """
    Registra o agente como autor da edição em cada arquivo listado.
    Chamado por run_task quando --files é fornecido.
    """
    nome  = agent.get("nome", "?")
    tier  = agent.get("tier", 1)
    model = agent.get("model", "?")
    ts    = _ts()

    try:
        if FILE_REGISTRY.exists():
            data = json.loads(FILE_REGISTRY.read_text(encoding="utf-8"))
        else:
            data = {"_schema": "1.0", "files": {}}

        reg = data.setdefault("files", {})
        for rel in files:
            rel = rel.strip().replace("\\", "/")
            if not rel:
                continue
            entry = reg.get(rel, {
                "owner":      nome,
                "created_by": nome,
                "created_ts": ts,
                "edit_count": 0,
                "co_authors": [],
            })
            entry["last_edited_by"] = nome
            entry["last_edit_ts"]   = ts
            entry["last_model"]     = model
            entry["last_tier"]      = tier
            entry["last_project"]   = project
            entry["edit_count"]     = entry.get("edit_count", 0) + 1
            co = entry.setdefault("co_authors", [])
            if nome not in co:
                co.append(nome)
            reg[rel] = entry

        FILE_REGISTRY.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  [file_registry] {len(files)} arquivo(s) registrados como editados por {nome}")
    except Exception as e:
        print(f"  [WARNING] Não foi possível atualizar file_registry: {e}")


# ---------------------------------------------------------------------------
# RAG signature — grava assinatura da tarefa no ChromaDB (squad_knowledge)
# ---------------------------------------------------------------------------

def write_rag_signature(agent: dict, task: str, response: str, project: str) -> None:
    """
    Indexa a tarefa + resposta no ChromaDB (squad_knowledge) com metadados de autoria.
    Falha silenciosamente se chromadb/sentence_transformers não estiverem disponíveis.
    """
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from sentence_transformers import SentenceTransformer

        nome  = agent.get("nome", "?")
        model = agent.get("model", "?")
        tier  = agent.get("tier", 1)
        ts    = _ts()

        db_path    = str(ROOT_DIR / "memory" / "chroma_db")
        chroma_cli = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        collection = chroma_cli.get_or_create_collection(
            name="squad_knowledge",
            metadata={"hnsw:space": "cosine"},
        )

        encoder  = SentenceTransformer("all-MiniLM-L6-v2")
        doc_text = (
            f"[TAREFA — {nome} | {ts}]\n"
            f"Projeto: {project}\n"
            f"Briefing: {task[:400]}\n"
            f"Resposta: {response[:600]}"
        )
        embedding = encoder.encode(doc_text).tolist()

        # ID único: agent + timestamp (sem colisão)
        doc_id = f"{nome.lower()}_{ts.replace(':', '').replace('-', '').replace('+', '')[:17]}"

        collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[doc_text],
            metadatas=[{
                "agent":    nome,
                "model":    model,
                "tier":     str(tier),
                "project":  project,
                "task_type": "agent_task",
                "timestamp": ts,
                "topic":    f"task/{nome.lower()}",
                "source":   "agent_runner",
            }],
        )
        print(f"  [rag_signature] ✅ Tarefa de {nome} indexada em squad_knowledge (id={doc_id})")
    except ImportError:
        pass  # chromadb/sentence_transformers não instalado — silencioso
    except Exception as e:
        print(f"  [WARNING] RAG signature falhou: {e}")


def retrieve_rag_context(agent_name: str, query: str) -> str:
    """Busca fragmentos de memória relevantes no ChromaDB local."""
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from sentence_transformers import SentenceTransformer

        db_path = str(ROOT_DIR / "memory" / "chroma_db")
        chroma_cli = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        encoder = SentenceTransformer("all-MiniLM-L6-v2")
        query_embedding = encoder.encode(query).tolist()

        docs = []

        # 1. Tenta recuperar do squad_knowledge
        try:
            collection = chroma_cli.get_collection(name="squad_knowledge")
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=3,
                include=["documents", "distances"]
            )
            if results and results.get("documents") and results["documents"][0]:
                for doc, dist in zip(results["documents"][0], results["distances"][0]):
                    if dist < 0.6:  # Similaridade razoável (distância cosseno)
                        docs.append(f"- [Memória Compartilhada] {doc}")
        except Exception:
            pass

        # 2. Tenta recuperar da memória específica do agente
        agent_collection_name = f"{agent_name.lower()}_memory"
        try:
            collection = chroma_cli.get_collection(name=agent_collection_name)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=2,
                include=["documents", "distances"]
            )
            if results and results.get("documents") and results["documents"][0]:
                for doc, dist in zip(results["documents"][0], results["distances"][0]):
                    if dist < 0.6:
                        docs.append(f"- [Memória do Agente] {doc}")
        except Exception:
            pass

        if docs:
            header = "\n" + "=" * 60 + "\n[CONTEXTO DE MEMÓRIA RECUPERADO (RAG)]\n"
            footer = "\n" + "=" * 60 + "\n"
            return header + "\n".join(docs) + footer
    except Exception as e:
        print(f"  [WARNING] Falha ao recuperar contexto RAG: {e}")
    return ""


def check_semantic_cache(agent_name: str, task: str) -> str | None:
    """Busca se a tarefa exata ou muito similar já foi respondida com sucesso."""
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from sentence_transformers import SentenceTransformer

        db_path = str(ROOT_DIR / "memory" / "chroma_db")
        chroma_cli = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # Cria ou obtém a coleção
        collection = chroma_cli.get_or_create_collection(
            name="semantic_cache",
            metadata={"hnsw:space": "cosine"},
        )
        if collection.count() == 0:
            return None

        encoder = SentenceTransformer("all-MiniLM-L6-v2")
        query_embedding = encoder.encode(task).tolist()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=1,
            where={"agent": agent_name},
            include=["documents", "distances"]
        )

        if results and results.get("documents") and results["documents"][0]:
            doc = results["documents"][0][0]
            dist = results["distances"][0][0]
            if dist < 0.08:  # Limite rígido para garantir que a tarefa é idêntica
                return doc
    except Exception as e:
        print(f"  [WARNING] Falha na busca de cache semântico: {e}")
    return None


def store_semantic_cache(agent_name: str, task: str, response: str, project: str) -> None:
    """Armazena o resultado de uma tarefa bem-sucedida no cache semântico."""
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from sentence_transformers import SentenceTransformer

        db_path = str(ROOT_DIR / "memory" / "chroma_db")
        chroma_cli = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        collection = chroma_cli.get_or_create_collection(
            name="semantic_cache",
            metadata={"hnsw:space": "cosine"},
        )

        encoder = SentenceTransformer("all-MiniLM-L6-v2")
        embedding = encoder.encode(task).tolist()

        ts = _ts()
        doc_id = f"cache_{agent_name.lower()}_{ts.replace(':', '').replace('-', '').replace('+', '')[:17]}"

        collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[response],
            metadatas=[{
                "agent": agent_name,
                "task": task[:500],
                "project": project,
                "timestamp": ts,
            }]
        )
        print(f"  [cache_semantico] ✅ Resultado de {agent_name} cacheado com sucesso (id={doc_id})")
    except Exception as e:
        print(f"  [WARNING] Falha ao gravar no cache semântico: {e}")


def is_task_simple(task: str) -> bool:
    """Verifica se uma tarefa é trivial (ex: saudações, tarefas muito curtas)."""
    words = task.strip().split()
    if len(words) < 15:
        return True
    
    simple_patterns = [
        r"^\s*ola\b", r"^\s*oi\b", r"^\s*hello\b", r"^\s*hi\b",
        r"apresente-se", r"quem e voce", r"test", r"teste"
    ]
    import re
    if any(re.search(pat, task, re.IGNORECASE) for pat in simple_patterns):
        return True
    
    return False


def execute_heuristic_task(task: str) -> dict:
    """Executa tarefas locais simples sem uso de LLM."""
    import subprocess
    task_lower = task.lower().strip()
    
    # 1. Formatação de arquivos
    if "format" in task_lower:
        words = task.split()
        file_to_format = None
        for w in words:
            if "." in w:
                file_to_format = w
                break
        if file_to_format:
            filepath = ROOT_DIR / file_to_format
            if filepath.exists():
                ext = filepath.suffix.lower()
                cmd = []
                if ext == ".py":
                    cmd = ["black", str(filepath)]
                elif ext in (".html", ".css", ".js", ".json"):
                    cmd = ["npx", "prettier", "--write", str(filepath)]
                
                if cmd:
                    try:
                        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                        if res.returncode == 0:
                            return {
                                "success": True,
                                "content": f"Arquivo {file_to_format} formatado localmente com sucesso usando: {' '.join(cmd)}.",
                                "finish_reason": "local",
                                "prompt_tokens": 0, "completion_tokens": 0
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"Formatador falhou: {res.stderr or res.stdout}",
                                "finish_reason": "error",
                                "prompt_tokens": 0, "completion_tokens": 0
                            }
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"Erro ao executar formatador: {e}",
                            "finish_reason": "error",
                            "prompt_tokens": 0, "completion_tokens": 0
                        }
            return {
                "success": False,
                "error": f"Arquivo '{file_to_format}' não encontrado.",
                "finish_reason": "error",
                "prompt_tokens": 0, "completion_tokens": 0
            }
    
    # 2. Limpeza básica de logs
    if "clean logs" in task_lower or "clear logs" in task_lower:
        log_file = ROOT_DIR / "project_ledger" / "hooks_audit.log"
        if log_file.exists():
            try:
                log_file.write_text("", encoding="utf-8")
                return {
                    "success": True,
                    "content": "Log hooks_audit.log limpo com sucesso localmente.",
                    "finish_reason": "local",
                    "prompt_tokens": 0, "completion_tokens": 0
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "finish_reason": "error",
                    "prompt_tokens": 0, "completion_tokens": 0
                }
    
    # 3. Executar comando local seguro (verificado)
    if task.startswith("LOCAL_RUN:"):
        cmd_str = task[10:].strip()
        allowed = ["git status", "git diff", "bandit", "python -m py_compile"]
        if any(cmd_str.startswith(a) for a in allowed):
            try:
                res = subprocess.run(cmd_str.split(), capture_output=True, text=True, timeout=15)
                return {
                    "success": res.returncode == 0,
                    "content": res.stdout or res.stderr,
                    "finish_reason": "local",
                    "prompt_tokens": 0, "completion_tokens": 0
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "finish_reason": "error",
                    "prompt_tokens": 0, "completion_tokens": 0
                }
        return {
            "success": False,
            "error": f"Comando local não autorizado. Autorizados: {allowed}",
            "finish_reason": "error",
            "prompt_tokens": 0, "completion_tokens": 0
        }
    
    return {
        "success": False,
        "error": f"Tarefa heurística não reconhecida. Use: 'format <arquivo>', 'clean logs', ou 'LOCAL_RUN: <comando>'",
        "finish_reason": "error",
        "prompt_tokens": 0, "completion_tokens": 0
    }


def parse_and_execute_dsl(dsl_text: str) -> list[str]:
    """Parseia a Mini-DSL e escreve os arquivos contidos."""
    import re
    written_files = []
    pattern = r"\[FILE:\s*(.+?)\]\s*\[CONTENT\](.*?)\[END_CONTENT\]"
    matches = re.findall(pattern, dsl_text, re.DOTALL)
    
    for filename, content in matches:
        filename = filename.strip()
        content = content.strip()
        filepath = ROOT_DIR / filename
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            written_files.append(filename)
        except Exception as e:
            print(f"  [WARNING] Erro ao escrever arquivo {filename} via DSL: {e}")
            
    return written_files


def run_task(agent_name: str, task: str, project: str, files: list[str] | None = None, use_rag: bool = False, use_dsl: bool = False) -> None:
    """Modo tarefa: delega briefing especifico a um agente e registra tudo."""
    is_heuristic = agent_name.lower() == "heuristic"
    if is_heuristic:
        agent = {
            "nome": "Heuristic",
            "tier": 1,
            "specialty": "Local Automation & Tasks",
            "model": "heuristic-local",
            "ruleset_version": "v1",
            "evolution": "Stable",
            "success_rate": 100.0,
            "status": "active",
            "pontos": {"externos": 0, "internos": 0},
            "tasks_completed": 0,
            "tasks_failed": 0,
            "_file": ""
        }
    else:
        agent = load_agent(agent_name)

    nome      = agent.get("nome", "?")
    model     = agent.get("model", "?")
    tier      = agent.get("tier", "?")
    evolution = agent.get("evolution", "Stable")
    sr        = agent.get("success_rate", 100)

    # Agentes Degraded nao recebem tarefas
    if evolution == "Degraded":
        print(f"[BLOQUEADO] {nome} esta em estado Degraded.")
        print("  Nenhuma tarefa nova sem aprovacao explicita do Arquiteto.")
        sys.exit(1)

    # 1. Roteamento Dinâmico (Complexity Routing)
    original_model = model
    if not is_heuristic and is_task_simple(task) and model in {"google/gemini-2.5-pro", "anthropic/claude-opus-4", "anthropic/claude-sonnet-4-5"}:
        model = "google/gemini-2.5-flash-lite"
        agent["model"] = model
        print(f"[ROUTING] Tarefa simples detectada. Roteando temporariamente de {original_model} para {model} para economizar custos.")

    # 2. Verifica Cache Semântico
    if not is_heuristic:
        cached_response = check_semantic_cache(nome, task)
        if cached_response:
            print("=" * 60)
            print(f"  RubberDuckFactory -- Task Runner [CACHE SEMÂNTICO DETECTADO]")
            print(f"  Agente  : {nome} (Tier {tier} | {evolution} | sr={sr}%)")
            print(f"  Projeto : {project or 'n/a'}")
            print("=" * 60)
            print()
            print(f"BRIEFING:\n{task}")
            print()
            print(f"[CACHE] Carregando resposta anterior do cache semântico (custo 0)...")
            print()
            print(f"RESPOSTA DE {nome.upper()}:")
            print("-" * 60)
            print(cached_response)
            print("-" * 60)
            print("Tokens: 0 in / 0 out | finish=cache | sr=100.0% (reutilizado)")
            print()
            write_task_ledger(agent, True, task, project, "Cached semantic response used.")
            write_history(agent, True, task, "Cached semantic response used.")
            return

    # 3. RAG Context Injection
    rag_context = ""
    if use_rag:
        print(f"[RAG] Procurando memórias similares para grounding...")
        rag_context = retrieve_rag_context(agent_name, task)
        if rag_context:
            print(f"[RAG] Contexto semântico injetado.")

    full_task = rag_context + task if rag_context else task

    # 4. LLM-DSL Instruction appending
    if use_dsl:
        full_task += (
            "\n\nIMPORTANT: Your response MUST be formatted strictly in the Mini-DSL syntax:\n"
            "[FILE: path/to/file]\n"
            "[CONTENT]\n"
            "(code contents here)\n"
            "[END_CONTENT]\n"
            "Do not write any markdown code blocks, conversations, or explanations. Just output the DSL."
        )

    print("=" * 60)
    print(f"  RubberDuckFactory -- Task Runner")
    print(f"  Agente  : {nome} (Tier {tier} | {evolution} | sr={sr}%)")
    print(f"  Modelo  : {model}")
    print(f"  Projeto : {project or 'n/a'}")
    print("=" * 60)
    print()
    if rag_context:
        print(rag_context.strip())
        print()
    print(f"BRIEFING:\n{task}")
    print()
    print(f"Chamando {nome}...")
    print()

    # 5. Executa Tarefa
    if is_heuristic:
        resultado = execute_heuristic_task(task)
    else:
        resultado = call_agent(agent, full_task)
        
    technical_success = resultado["success"]

    # Custo
    record_cost(
        agent=nome, model=model, task=task[:80],
        prompt_tokens=resultado["prompt_tokens"],
        completion_tokens=resultado["completion_tokens"],
    )

    # Stats, evolucao, ledger e historico
    if is_heuristic:
        updated = agent
        write_task_ledger(agent, technical_success, task, project, resultado.get("error") or "")
        write_history(agent, technical_success, task, resultado.get("error") or "")
    else:
        updated = update_agent_stats(agent, technical_success)
        write_task_ledger(agent, technical_success, task, project, resultado.get("error") or "")
        write_history(agent, technical_success, task, resultado.get("error") or "")

    # Assinatura RAG + file registry + cache semântico
    if technical_success and not is_heuristic:
        write_rag_signature(agent, task, resultado["content"], project)
        store_semantic_cache(nome, task, resultado["content"], project)
        
        # DSL Parsing se ativado
        if use_dsl:
            written = parse_and_execute_dsl(resultado["content"])
            if written:
                print(f"  [DSL PARSER] ✅ Arquivos gerados via DSL: {', '.join(written)}")
                if files is None:
                    files = []
                files.extend(written)

        if files:
            update_file_registry(files, agent, project)

    # Output
    if technical_success:
        print(f"RESPOSTA DE {nome.upper()}:")
        print("-" * 60)
        print(resultado["content"])
        print("-" * 60)
        new_sr  = updated.get("success_rate", sr)
        ok_cnt  = updated.get("tasks_completed", 0)
        fail_cnt = updated.get("tasks_failed", 0)
        print(
            f"Tokens: {resultado['prompt_tokens']} in / {resultado['completion_tokens']} out"
            f" | finish={resultado['finish_reason'] if not is_heuristic else 'local'}"
            f" | sr={new_sr}% ({ok_cnt}ok/{fail_cnt}fail)"
        )
    else:
        print(f"ERRO: {resultado['error']}")

    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="RubberDuckFactory Agent Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  uv run python agents/agent_runner.py\n"
            "  uv run python agents/agent_runner.py --agent chen --task 'Criar endpoint POST /items'\n"
            "  uv run python agents/agent_runner.py -a nova -t 'Refatorar Card' -p 'ClienteXYZ'\n"
        ),
    )
    parser.add_argument("--agent",   "-a", metavar="NOME",
                        help="Nome do agente (ex: chen, nova, shadow)")
    parser.add_argument("--task",    "-t", metavar="BRIEFING",
                        help="Briefing/tarefa para o agente")
    parser.add_argument("--project", "-p", metavar="PROJETO",
                        default="RubberDuckFactory",
                        help="Nome do projeto para o ledger (padrao: RubberDuckFactory)")
    parser.add_argument("--files",   "-f", metavar="ARQ[,ARQ]",
                        help="Arquivos tocados pela tarefa, separados por vírgula "
                             "(atualiza file_registry com autoria do agente)")
    parser.add_argument("--rag", action="store_true",
                        help="Ativa a recuperação de contexto semântico (RAG)")
    parser.add_argument("--dsl", action="store_true",
                        help="Usa Mini-DSL estruturada para economizar tokens de output")

    args = parser.parse_args()

    if args.agent and args.task:
        files = [f.strip() for f in args.files.split(",")] if args.files else None
        run_task(args.agent, args.task, args.project, files, args.rag, args.dsl)
    elif args.agent or args.task:
        parser.error("Use --agent e --task juntos, ou nenhum (modo hello-world).")
    else:
        run_hello_world()


if __name__ == "__main__":
    main()
