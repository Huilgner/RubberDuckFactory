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
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 stdout to avoid cp1252 encoding errors on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
from cost_tracker import record_cost, assert_budget_ok, BudgetExceededError
from ledger_io import append_history
from fitness_math import EVOLUTION_WINDOW, rolling_success_rate

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------

ROOT_DIR       = Path(__file__).parent.parent
AGENTS_DIR     = ROOT_DIR / "agents" / "active"
POOL_DIR       = ROOT_DIR / "agents" / "pool"
LEDGER_DIR     = ROOT_DIR / "project_ledger"
FILE_REGISTRY  = LEDGER_DIR / "file_registry.json"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

load_dotenv(ROOT_DIR / ".env")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
# A ausencia da key so falha na hora de CHAMAR um agente (call_agent) --
# importar o modulo, rodar testes e usar o agente heuristic funcionam sem ela.

# Tokens maximos por modelo -- Gemini 2.5 Pro consome muitos tokens de raciocinio
MODEL_MAX_TOKENS: dict[str, int] = {
    "google/gemini-2.5-pro":           8000,
    "google/gemini-2.5-flash":         4000,
    "google/gemini-2.5-flash-lite":    2000,
    "deepseek/deepseek-chat":          4000,
    "deepseek/deepseek-v4-flash:free": 2000,
    "anthropic/claude-opus-4":         4000,
    "anthropic/claude-sonnet-4-5":     6000,
    "anthropic/claude-fable-5":        16000,
}
DEFAULT_MAX_TOKENS = 3000

TIER_NAMES = {1: "Observer", 2: "Operator", 3: "Specialist", 4: "Architect"}

# Fable 5 como orquestrador sob demanda (opt-in): "RDF_FABLE <tarefa>"
FABLE_MODEL = "anthropic/claude-fable-5"
FABLE_TRIGGER_RE = re.compile(r"^\s*RDF_FABLE\b[:\s]*", re.IGNORECASE)


def _model_rejects_sampling(model: str) -> bool:
    """Fable 5 e Opus 4.7+ removeram temperature/top_p/top_k -> enviar retorna HTTP 400."""
    m = model.lower()
    return any(tag in m for tag in ("claude-fable-5", "claude-opus-4-7", "claude-opus-4-8"))


# ---------------------------------------------------------------------------
# Carregamento de agentes
# ---------------------------------------------------------------------------

def _bootstrap_active_from_pool() -> None:
    """
    agents/active/ e local (gitignored); agents/pool/ e o genoma versionado.
    Em um clone novo, inicializa o squad local a partir do pool automaticamente.
    """
    if AGENTS_DIR.exists() and any(AGENTS_DIR.glob("*.json")):
        return
    if not POOL_DIR.exists():
        return
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    seeded = 0
    for src in sorted(POOL_DIR.glob("*.json")):
        dst = AGENTS_DIR / src.name
        if not dst.exists():
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            seeded += 1
    if seeded:
        print(f"[BOOTSTRAP] Squad local vazio -> {seeded} agente(s) inicializado(s) a partir de agents/pool/")


def load_agent(name: str) -> dict:
    """Carrega um agente pelo nome (case-insensitive). Levanta SystemExit se nao encontrado."""
    _bootstrap_active_from_pool()
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
    _bootstrap_active_from_pool()
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

# Status HTTP transitorios (infra): valem retry e NAO penalizam o agente
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
MAX_API_ATTEMPTS = 3
RETRY_BACKOFF_S  = [2, 5]  # espera antes da 2a e da 3a tentativa


def _api_failure(error: str, infra: bool) -> dict:
    return {
        "content": "", "finish_reason": "error",
        "prompt_tokens": 0, "completion_tokens": 0,
        "success": False, "infra_failure": infra, "error": error,
    }


def call_agent(agent: dict, user_message: str, max_tokens: int | None = None,
               response_format: dict | None = None) -> dict:
    """
    Chama o agente via OpenRouter, com retry/backoff para falhas transitorias.
    Retorna: {content, finish_reason, prompt_tokens, completion_tokens,
              success, infra_failure, error}

    response_format: opcional, ex. {"type": "json_object"} para saida JSON
    estruturada (modelos que nao suportam retornam 400 -> chamador faz fallback).

    infra_failure=True -> a falha e da infraestrutura (429/5xx/timeout/rede apos
    retries), nao do modelo. O chamador NAO deve penalizar o agente nesse caso.
    """
    if not OPENROUTER_API_KEY:
        raise SystemExit(
            "OPENROUTER_API_KEY nao encontrada no .env\n"
            "Preencha o arquivo .env com: OPENROUTER_API_KEY=sk-or-v1-..."
        )

    # Guardrail de orcamento: teto atingido = nenhuma chamada de API sai
    try:
        assert_budget_ok()
    except BudgetExceededError as e:
        raise SystemExit(f"[ORCAMENTO] Chamada bloqueada: {e}")

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
        "max_tokens":  max_tokens,
    }
    # Fable 5 / Opus 4.7+ removeram sampling params -> enviar temperature retorna HTTP 400.
    if not _model_rejects_sampling(model):
        payload["temperature"] = 0.3
    if response_format:
        payload["response_format"] = response_format

    last_error = ""
    for attempt in range(1, MAX_API_ATTEMPTS + 1):
        try:
            with httpx.Client(timeout=180.0) as client:
                resp = client.post(OPENROUTER_URL, headers=headers, json=payload)

                if resp.status_code in RETRYABLE_STATUS:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                    if attempt < MAX_API_ATTEMPTS:
                        wait = RETRY_BACKOFF_S[attempt - 1]
                        print(f"  [RETRY] {last_error[:80]} -> tentativa {attempt + 1}/{MAX_API_ATTEMPTS} em {wait}s")
                        time.sleep(wait)
                        continue
                    return _api_failure(f"{last_error} (apos {MAX_API_ATTEMPTS} tentativas)", infra=True)

                resp.raise_for_status()
                data  = resp.json()
                usage = data.get("usage", {})
                return {
                    "content":           (data["choices"][0]["message"]["content"] or "").strip(),
                    "finish_reason":     data["choices"][0].get("finish_reason", "?"),
                    "prompt_tokens":     usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "success":           True,
                    "infra_failure":     False,
                    "error":             None,
                }
        except httpx.HTTPStatusError as e:
            # 4xx nao-transitorio (payload invalido, modelo inexistente, auth):
            # falha imediata, atribuivel a configuracao/modelo -- sem retry.
            return _api_failure(f"HTTP {e.response.status_code}: {e.response.text[:300]}", infra=False)
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last_error = f"{type(e).__name__}: {e}"
            if attempt < MAX_API_ATTEMPTS:
                wait = RETRY_BACKOFF_S[attempt - 1]
                print(f"  [RETRY] {last_error[:80]} -> tentativa {attempt + 1}/{MAX_API_ATTEMPTS} em {wait}s")
                time.sleep(wait)
                continue
            return _api_failure(f"{last_error} (apos {MAX_API_ATTEMPTS} tentativas)", infra=True)
        except Exception as e:
            return _api_failure(str(e), infra=False)

    return _api_failure(last_error or "falha desconhecida", infra=True)


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
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def update_agent_stats(agent: dict, technical_success: bool) -> dict:
    """
    Incrementa tasks_completed ou tasks_failed, recalcula success_rate (vitalicio,
    historico) e aplica transicao de evolucao pela JANELA DESLIZANTE das ultimas
    tarefas (fitness_math.EVOLUTION_WINDOW) -- 10 falhas recentes nao podem ser
    diluidas por 200 acertos antigos. Retorna o dict atualizado.
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

    # Janela deslizante: 0/1 por tarefa, mais recente por ultimo
    recent = list(d.get("recent_results", []))
    recent.append(1 if technical_success else 0)
    d["recent_results"] = recent[-EVOLUTION_WINDOW:]

    # Transicao de evolucao pela janela (exige amostra minima; antes disso mantem o estado)
    window_sr = rolling_success_rate(d["recent_results"])
    old_evolution = d.get("evolution", "Stable")
    new_evolution = _compute_evolution(window_sr) if window_sr is not None else old_evolution
    if new_evolution != old_evolution:
        d["evolution"] = new_evolution
        _append_ledger({
            "ts":           _ts(),
            "type":         "EVOLUCAO",
            "agent":        d.get("nome", "?"),
            "from":         old_evolution,
            "to":           new_evolution,
            "success_rate": d.get("success_rate"),
            "window_sr":    window_sr,
            "window_n":     len(d["recent_results"]),
            "trigger":      "agent_runner_janela_deslizante",
        })
        print(f"[EVOLUCAO] {d.get('nome','?')}: {old_evolution} -> {new_evolution} "
              f"(janela={window_sr}% em {len(d['recent_results'])} tarefas | vitalicio={d.get('success_rate')}%)")

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
    """Escreve TASK_SUCCESS ou TASK_FAILURE no historico (via ledger_io, sob lock)."""
    entry: dict = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "type":      "TASK_SUCCESS" if success else "TASK_FAILURE",
        "agent":     agent.get("nome", "?"),
        "task":      task[:200],
    }
    if not success and error:
        entry["reason"] = error[:200]
    try:
        append_history(entry)
    except Exception as e:
        print(f"  [WARNING] Nao foi possivel gravar no historico: {e}")


def write_infra_event(agent: dict, task: str, error: str, project: str = "") -> None:
    """
    Registra falha de INFRAESTRUTURA (API fora, 429/5xx, timeout apos retries).
    Evento separado de TAREFA_FALHA/TASK_FAILURE: nao conta contra o
    success_rate do agente -- a falha nao e atribuivel ao modelo.
    """
    _append_ledger({
        "ts":      _ts(),
        "type":    "INFRA_FALHA",
        "agent":   agent.get("nome", "?"),
        "project": project or "n/a",
        "reason":  (error or "")[:200],
    })
    try:
        append_history({
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "type":      "INFRA_FAILURE",
            "agent":     agent.get("nome", "?"),
            "task":      task[:200],
            "reason":    (error or "")[:200],
        })
    except Exception as e:
        print(f"  [WARNING] Nao foi possivel gravar no historico: {e}")


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

def _load_fallback_data() -> dict:
    fallback_file = ROOT_DIR / "project_ledger" / "local_memory_fallback.json"
    if not fallback_file.exists():
        return {"semantic_cache": {}, "squad_knowledge": []}
    try:
        return json.loads(fallback_file.read_text(encoding="utf-8"))
    except Exception:
        return {"semantic_cache": {}, "squad_knowledge": []}


def _save_fallback_data(data: dict) -> None:
    fallback_file = ROOT_DIR / "project_ledger" / "local_memory_fallback.json"
    try:
        fallback_file.parent.mkdir(parents=True, exist_ok=True)
        fallback_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"  [WARNING] Não foi possível gravar no fallback de memória local: {e}")


def write_rag_signature(agent: dict, task: str, response: str, project: str) -> None:
    """
    Indexa a tarefa + resposta no Qdrant central e grava no fallback local.
    """
    nome = agent.get("nome", "?")
    ts = _ts()
    doc_text = (
        f"[TAREFA — {nome} | {ts}]\n"
        f"Projeto: {project}\n"
        f"Briefing: {task[:400]}\n"
        f"Resposta: {response[:600]}"
    )
    
    server_success = False
    # 1. Tenta gravar no Qdrant central via servidor MCP
    try:
        import httpx
        url = "http://localhost:8001/api/remember"
        payload = {
            "agent": "squad_knowledge",
            "content": doc_text,
            "metadata": {
                "agent": nome,
                "model": agent.get("model", "?"),
                "tier": str(agent.get("tier", 1)),
                "project": project,
                "task_type": "agent_task",
                "timestamp": ts,
                "topic": f"task/{nome.lower()}",
                "source": "agent_runner"
            }
        }
        resp = httpx.post(url, json=payload, timeout=2.0)
        if resp.status_code == 200:
            server_success = True
            print(f"  [rag_signature] ✅ Tarefa indexada no Qdrant central")
    except Exception:
        pass

    # 2. Grava no fallback local
    try:
        data = _load_fallback_data()
        squad = data.setdefault("squad_knowledge", [])
        
        # Limita o tamanho do fallback local para não crescer infinitamente (manter as últimas 100 memórias)
        if len(squad) >= 100:
            squad.pop(0)
            
        squad.append({
            "agent": nome,
            "content": doc_text,
            "project": project,
            "timestamp": ts
        })
        _save_fallback_data(data)
        if not server_success:
            print(f"  [rag_signature] ⚠️ Servidor offline. Salvo localmente no JSON de fallback.")
    except Exception as e:
        print(f"  [WARNING] Falha ao gravar assinatura RAG local: {e}")


def retrieve_rag_context(agent_name: str, query: str) -> str:
    """Busca fragmentos de memória relevantes no Qdrant central ou fallback local."""
    docs = []
    
    # 1. Tenta recuperar via servidor MCP
    try:
        import httpx
        url = "http://localhost:8001/api/recall"
        
        # Busca no squad_knowledge
        resp = httpx.post(url, json={"agent": "squad_knowledge", "query": query, "top_k": 3}, timeout=3.0)
        if resp.status_code == 200:
            results = resp.json()
            for r in results:
                if r.get("score", 0.0) >= 0.6:
                    docs.append(f"- [Memória Compartilhada] {r.get('content')}")
                    
        # Busca na memória específica do agente
        resp = httpx.post(url, json={"agent": agent_name, "query": query, "top_k": 2}, timeout=3.0)
        if resp.status_code == 200:
            results = resp.json()
            for r in results:
                if r.get("score", 0.0) >= 0.6:
                    docs.append(f"- [Memória do Agente] {r.get('content')}")
                    
    except Exception:
        # Fallback offline usando busca heurística por palavras-chave
        try:
            data = _load_fallback_data()
            squad_memories = data.get("squad_knowledge", [])
            query_words = set(query.lower().split())
            
            scored_docs = []
            for mem in squad_memories:
                content = mem.get("content", "")
                if not content:
                    continue
                content_words = set(content.lower().split())
                intersection = query_words.intersection(content_words)
                if intersection:
                    score = len(intersection) / len(query_words)
                    is_shared = mem.get("agent", "").lower() != agent_name.lower()
                    scored_docs.append((score, is_shared, content))
            
            scored_docs.sort(key=lambda x: x[0], reverse=True)
            for score, is_shared, content in scored_docs[:3]:
                if score > 0.15:
                    prefix = "Memória Compartilhada" if is_shared else "Memória do Agente"
                    docs.append(f"- [Fallback Local: {prefix}] {content}")
        except Exception:
            pass

    if docs:
        header = "\n" + "=" * 60 + "\n[CONTEXTO DE MEMÓRIA RECUPERADO (RAG)]\n"
        footer = "\n" + "=" * 60 + "\n"
        return header + "\n".join(docs) + footer
    return ""


def check_semantic_cache(agent_name: str, task: str) -> str | None:
    """Busca se a tarefa exata ou muito similar já foi respondida com sucesso."""
    try:
        import httpx
        url = "http://localhost:8001/api/semantic_cache/get"
        payload = {"agent": agent_name, "task": task}
        resp = httpx.post(url, json=payload, timeout=2.0)
        if resp.status_code == 200:
            res_data = resp.json()
            if res_data.get("cached"):
                return res_data.get("content")
    except Exception:
        pass

    # Fallback local (comparação exata de string limpa)
    try:
        data = _load_fallback_data()
        cache = data.get("semantic_cache", {}).get(agent_name.lower(), {})
        task_clean = task.strip().lower()
        if task_clean in cache:
            return cache[task_clean]
        
        # Similaridade heurística Jaccard para palavras
        for cached_task, cached_resp in cache.items():
            if len(cached_task) == 0:
                continue
            words_a = set(task_clean.split())
            words_b = set(cached_task.split())
            if not words_a or not words_b:
                continue
            intersection = words_a.intersection(words_b)
            union = words_a.union(words_b)
            jaccard = len(intersection) / len(union)
            if jaccard > 0.90:
                return cached_resp
    except Exception:
        pass
    return None


def store_semantic_cache(agent_name: str, task: str, response: str, project: str) -> None:
    """Armazena o resultado de uma tarefa bem-sucedida no cache semântico."""
    server_success = False
    try:
        import httpx
        url = "http://localhost:8001/api/semantic_cache/set"
        payload = {"agent": agent_name, "task": task, "response": response, "project": project}
        resp = httpx.post(url, json=payload, timeout=2.0)
        if resp.status_code == 200:
            server_success = True
            print(f"  [cache_semantico] ✅ Gravado no Qdrant central")
    except Exception:
        pass

    # Gravação no fallback local
    try:
        data = _load_fallback_data()
        cache = data.setdefault("semantic_cache", {}).setdefault(agent_name.lower(), {})
        cache[task.strip().lower()] = response
        _save_fallback_data(data)
        if not server_success:
            print(f"  [cache_semantico] ⚠️ Servidor offline. Gravado localmente no JSON de fallback.")
    except Exception as e:
        print(f"  [WARNING] Falha ao gravar no cache semântico local: {e}")


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
    """Parseia a Mini-DSL e escreve os arquivos contidos (restritos a raiz do projeto)."""
    import re
    written_files = []
    pattern = r"\[FILE:\s*(.+?)\]\s*\[CONTENT\](.*?)\[END_CONTENT\]"
    matches = re.findall(pattern, dsl_text, re.DOTALL)

    project_root = ROOT_DIR.resolve()
    for filename, content in matches:
        filename = filename.strip()
        content = content.strip()
        filepath = (ROOT_DIR / filename).resolve()
        # Guardrail: output do LLM nao pode escrever fora da raiz do projeto
        if not filepath.is_relative_to(project_root):
            print(f"  [BLOQUEADO] DSL tentou escrever fora do projeto: {filename}")
            continue
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            written_files.append(filename)
        except Exception as e:
            print(f"  [WARNING] Erro ao escrever arquivo {filename} via DSL: {e}")

    return written_files


def validate_artifacts(paths: list[str]) -> tuple[bool, list[dict]]:
    """
    Validacao deterministica dos artefatos gerados por agente (ADR-003: sinal
    de sucesso tecnico baseado em verificacao, nao em "respondeu algo").

      .py            -> compile() (checagem de sintaxe)
      .json          -> json.loads
      .yaml / .yml   -> yaml.safe_load (se pyyaml disponivel)
      .js/.mjs/.cjs  -> node --check (se node disponivel)
      outros         -> 'skipped' (sem validador deterministico)

    Retorna (todos_validos, [{file, status, detail}, ...]).
    'skipped' nao reprova; apenas 'fail' derruba o sucesso tecnico.
    """
    results: list[dict] = []
    all_ok = True

    for rel in paths:
        fp = ROOT_DIR / rel
        ext = fp.suffix.lower()
        status, detail = "skipped", ""
        try:
            src = fp.read_text(encoding="utf-8")
            if ext == ".py":
                compile(src, str(fp), "exec")
                status = "ok"
            elif ext == ".json":
                json.loads(src)
                status = "ok"
            elif ext in (".yaml", ".yml"):
                try:
                    import yaml
                    yaml.safe_load(src)
                    status = "ok"
                except ImportError:
                    detail = "pyyaml nao instalado"
            elif ext in (".js", ".mjs", ".cjs"):
                import shutil
                import subprocess
                node = shutil.which("node")
                if node:
                    r = subprocess.run([node, "--check", str(fp)],
                                       capture_output=True, text=True, timeout=15)
                    if r.returncode == 0:
                        status = "ok"
                    else:
                        status, detail = "fail", (r.stderr or r.stdout)[:200]
                else:
                    detail = "node nao encontrado"
        except SyntaxError as e:
            status, detail = "fail", f"sintaxe invalida: {e}"
        except json.JSONDecodeError as e:
            status, detail = "fail", f"JSON invalido: {e}"
        except Exception as e:
            status, detail = "fail", str(e)[:200]

        if status == "fail":
            all_ok = False
        results.append({"file": rel, "status": status, "detail": detail})

    return all_ok, results


MAX_CONTEXT_PER_FILE = 8_000    # chars por arquivo injetado no briefing
MAX_CONTEXT_TOTAL    = 24_000   # chars totais de contexto de arquivos


def build_files_context(files: list[str] | None) -> str:
    """
    Injeta o CONTEUDO dos arquivos existentes de --files no briefing, para o
    agente enxergar o codigo que vai modificar (agentes cegos sao a causa raiz
    de alucinacao tipo 'caso Echo'). Arquivos inexistentes sao ignorados em
    silencio -- presume-se que sao saidas a criar. Caps de tamanho evitam
    estourar o orcamento de tokens.
    """
    if not files:
        return ""
    project_root = ROOT_DIR.resolve()
    blocks: list[str] = []
    used = 0
    for rel in files:
        rel = rel.strip()
        if not rel:
            continue
        fp = (ROOT_DIR / rel).resolve()
        if not fp.is_relative_to(project_root) or not fp.is_file():
            continue
        try:
            content = fp.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        truncated = len(content) > MAX_CONTEXT_PER_FILE
        content = content[:MAX_CONTEXT_PER_FILE]
        if used + len(content) > MAX_CONTEXT_TOTAL:
            content = content[: max(0, MAX_CONTEXT_TOTAL - used)]
            truncated = True
        if not content:
            break
        used += len(content)
        note = " (TRUNCADO)" if truncated else ""
        blocks.append(f"--- {rel}{note} ---\n{content}")
        if used >= MAX_CONTEXT_TOTAL:
            break
    if not blocks:
        return ""
    return (
        "### CONTEXTO — CONTEUDO ATUAL DOS ARQUIVOS ENVOLVIDOS ###\n"
        "Baseie-se EXATAMENTE neste conteudo; nao invente codigo que nao esta aqui.\n\n"
        + "\n\n".join(blocks)
        + "\n### FIM DO CONTEXTO ###\n\n"
    )


def run_task(agent_name: str, task: str, project: str, files: list[str] | None = None, use_rag: bool = False, use_dsl: bool = False) -> None:
    """Modo tarefa: delega briefing especifico a um agente e registra tudo."""
    is_heuristic = agent_name.lower() == "heuristic"
    is_fable     = agent_name.lower() == "fable"
    is_synthetic = is_heuristic or is_fable
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
    elif is_fable:
        # Orquestrador soberano sob demanda — agente sintético, não persistido em JSON.
        agent = {
            "nome": "Fable",
            "tier": 4,
            "specialty": "Sovereign Orchestrator / Architect",
            "model": FABLE_MODEL,
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
    if not is_synthetic and is_task_simple(task) and model in {"google/gemini-2.5-pro", "anthropic/claude-opus-4", "anthropic/claude-sonnet-4-5"}:
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

    # 3b. Contexto dos arquivos de --files: o agente ve o codigo que vai tocar
    files_context = "" if is_heuristic else build_files_context(files)
    if files_context:
        print(f"[CONTEXTO] {files_context.count('--- ')} arquivo(s) injetado(s) no briefing "
              f"({len(files_context)} chars)")

    full_task = files_context + rag_context + task if (rag_context or files_context) else task

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

    # 5a. Falha de infraestrutura (429/5xx/timeout apos retries): registra evento
    # proprio e NAO penaliza o agente -- a falha nao e atribuivel ao modelo.
    if resultado.get("infra_failure"):
        print(f"[INFRA] Falha de infraestrutura: {resultado.get('error')}")
        print("  Evento INFRA_FALHA registrado. Stats do agente preservados.")
        write_infra_event(agent, task, resultado.get("error") or "", project)
        sys.exit(1)

    technical_success = bool(resultado["success"])

    # 5b. Resposta truncada nao e entrega valida
    if technical_success and not is_heuristic and resultado.get("finish_reason") == "length":
        technical_success = False
        resultado["error"] = "saida truncada (finish_reason=length)"
        print("  [VALIDACAO] Resposta truncada pelo limite de tokens -> tarefa marcada como falha.")

    # 5c. DSL: parse + validacao deterministica ANTES de computar stats,
    # para que o sinal de sucesso reflita artefatos verificados (nao so "respondeu").
    written: list[str] = []
    if technical_success and not is_heuristic and use_dsl:
        written = parse_and_execute_dsl(resultado["content"])
        if written:
            all_ok, val_results = validate_artifacts(written)
            for v in val_results:
                mark = {"ok": "✅", "fail": "❌", "skipped": "—"}.get(v["status"], "?")
                extra = f" ({v['detail']})" if v["detail"] else ""
                print(f"  [VALIDACAO] {mark} {v['file']}: {v['status']}{extra}")
            if not all_ok:
                technical_success = False
                bad = ", ".join(f"{v['file']}: {v['detail']}" for v in val_results if v["status"] == "fail")
                resultado["error"] = f"artefato invalido -> {bad}"[:300]
            else:
                print(f"  [DSL PARSER] ✅ Arquivos gerados via DSL: {', '.join(written)}")
                if files is None:
                    files = []
                files.extend(written)
        else:
            technical_success = False
            resultado["error"] = "modo DSL ativo mas nenhum bloco [FILE:...] valido na resposta"

    # Custo
    record_cost(
        agent=nome, model=model, task=task[:80],
        prompt_tokens=resultado["prompt_tokens"],
        completion_tokens=resultado["completion_tokens"],
    )

    # Stats, evolucao, ledger e historico
    if is_synthetic:
        updated = agent
        write_task_ledger(agent, technical_success, task, project, resultado.get("error") or "")
        write_history(agent, technical_success, task, resultado.get("error") or "")
    else:
        updated = update_agent_stats(agent, technical_success)
        write_task_ledger(agent, technical_success, task, project, resultado.get("error") or "")
        write_history(agent, technical_success, task, resultado.get("error") or "")

    # Assinatura RAG + file registry + cache semântico (so para entregas validadas --
    # nunca cachear/assinar output reprovado na validacao)
    if technical_success and not is_heuristic:
        write_rag_signature(agent, task, resultado["content"], project)
        store_semantic_cache(nome, task, resultado["content"], project)
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

    # Gatilho opt-in: "RDF_FABLE <tarefa>" -> Fable 5 como orquestrador (Architect Tier 4).
    # Dispensa --agent; ignora a hierarquia de delegação normal (opus/gemini).
    if args.task and FABLE_TRIGGER_RE.match(args.task):
        clean_task = FABLE_TRIGGER_RE.sub("", args.task, count=1).strip()
        if not clean_task:
            parser.error("RDF_FABLE exige uma tarefa apos o gatilho. Ex: --task 'RDF_FABLE Refatorar modulo X'")
        files = [f.strip() for f in args.files.split(",")] if args.files else None
        run_task("fable", clean_task, args.project, files, args.rag, args.dsl)
        return

    if args.agent and args.task:
        files = [f.strip() for f in args.files.split(",")] if args.files else None
        run_task(args.agent, args.task, args.project, files, args.rag, args.dsl)
    elif args.agent or args.task:
        parser.error("Use --agent e --task juntos, ou nenhum (modo hello-world).")
    else:
        run_hello_world()


if __name__ == "__main__":
    main()
