#!/usr/bin/env python3
"""
memory/sync_history.py — Sincroniza logs do history.json no banco vetorial Qdrant central.
Aplica o Filtro de Commit e Consolidação Epistêmica (evita poluição com erros intermediários).
"""

import sys
import os
import json
import uuid
from pathlib import Path
from datetime import datetime

# Force UTF-8 stdout to avoid encoding errors on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
LEDGER_PATH = ROOT_DIR / "project_ledger" / "history.json"
SERVER_URL = "http://localhost:8001/api/remember"

load_dotenv(ROOT_DIR / ".env")

def generate_deterministic_uuid(namespace_str: str, name_str: str) -> str:
    """Gera um UUID determinístico v5 para evitar duplicação no Qdrant."""
    namespace = uuid.UUID(namespace_str)
    return str(uuid.uuid5(namespace, name_str))

def sync():
    print("🔄 Iniciando sincronização do history.json com a memória vetorial central...")
    
    if not LEDGER_PATH.exists():
        print(f"❌ Arquivo history.json não encontrado em: {LEDGER_PATH}")
        sys.exit(1)
        
    try:
        data = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Erro ao ler history.json: {e}")
        sys.exit(1)
        
    logs = data.get("logs", [])
    if not logs:
        print("ℹ️ Nenhum log encontrado para sincronizar.")
        return

    # Filtro de Commit e Consolidação Epistêmica:
    # Apenas indexamos sucessos de tarefas (TASK_SUCCESS) e prompts humanos de alto nível (HUMAN_PROMPT).
    # Excluímos custos lineares (COST_RECORD) e erros brutos intermediários de tarefas falhas (TASK_FAILURE).
    valid_types = {"TASK_SUCCESS", "HUMAN_PROMPT"}
    filtered_logs = [log for log in logs if log.get("type") in valid_types]
    
    print(f"📋 Encontrados {len(logs)} logs totais. {len(filtered_logs)} logs de interesse (Sucesso e Prompts).")
    
    # Namespace fixo para gerar UUIDs determinísticos
    NAMESPACE_MEM = "3b5d2522-86ee-4df6-8db8-1b5e135cf57e"
    
    success_count = 0
    fail_count = 0
    
    # Testa se o servidor está online primeiro
    try:
        # Ping simples ou tenta conectar
        with httpx.Client(timeout=3.0) as client:
            # Mandamos um post vazio para testar se responde (esperamos 400 ou 500 ou sucesso se passasse dados)
            resp = client.post(SERVER_URL, json={})
    except Exception as e:
        print(f"❌ Erro: Servidor FastMCP offline (porta 8001). Certifique-se de que o Docker está rodando e execute 'docker compose up -d'. Detalhes: {e}")
        sys.exit(1)
        
    for log in filtered_logs:
        timestamp = log.get("timestamp", "")
        log_type = log.get("type", "")
        
        if log_type == "HUMAN_PROMPT":
            prompt_text = log.get("prompt", "")
            if not prompt_text:
                continue
            doc_text = f"[HUMAN PROMPT — {timestamp}]\nPrompt: {prompt_text}"
            metadata = {
                "type": "human_prompt",
                "timestamp": timestamp,
                "source": "history_sync"
            }
            doc_key = f"prompt_{timestamp}_{prompt_text[:100]}"
        elif log_type == "TASK_SUCCESS":
            agent = log.get("agent", "?")
            task = log.get("task", "")
            if not task:
                continue
            doc_text = f"[SUCESSO — {agent} | {timestamp}]\nTarefa: {task}"
            metadata = {
                "type": "task_success",
                "agent": agent,
                "timestamp": timestamp,
                "source": "history_sync"
            }
            doc_key = f"success_{timestamp}_{agent}_{task[:100]}"
        else:
            continue
            
        doc_id = generate_deterministic_uuid(NAMESPACE_MEM, doc_key)
        
        payload = {
            "agent": "squad_knowledge",
            "content": doc_text,
            "metadata": metadata,
            "id": doc_id
        }
        
        try:
            resp = httpx.post(SERVER_URL, json=payload, timeout=5.0)
            if resp.status_code == 200:
                success_count += 1
            else:
                print(f"⚠️ Falha ao sincronizar log {doc_key[:40]}: HTTP {resp.status_code} - {resp.text}")
                fail_count += 1
        except Exception as e:
            print(f"⚠️ Erro ao enviar log {doc_key[:40]}: {e}")
            fail_count += 1
            
    print(f"✅ Sincronização concluída! {success_count} logs gravados/atualizados no Qdrant central, {fail_count} falhas.")

if __name__ == "__main__":
    sync()
