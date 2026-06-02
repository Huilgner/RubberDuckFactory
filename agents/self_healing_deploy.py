#!/usr/bin/env python3
"""
agents/self_healing_deploy.py -- Loop de Auto-Correção de Qualidade (Self-Healing Deploy Gate)
"""

import sys

# Force UTF-8 stdout to avoid cp1252 encoding errors on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from agent_runner import load_agent, call_agent, update_file_registry

ROOT_DIR = Path(__file__).parent.parent
LEDGER_DIR = ROOT_DIR / "project_ledger"

def write_history(entry: dict) -> None:
    history_file = LEDGER_DIR / "history.json"
    if not history_file.exists():
        return
    try:
        data = json.loads(history_file.read_text(encoding="utf-8"))
        data.setdefault("logs", []).append(entry)
        history_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"  [WARNING] Não foi possível escrever no history.json: {e}")

FILE_REGISTRY = LEDGER_DIR / "file_registry.json"

def run_sast_scan() -> dict:
    """Executa o bandit SAST para encontrar problemas de segurança."""
    scan_target = str(ROOT_DIR)
    exclude = str(ROOT_DIR / ".venv") + "," + str(ROOT_DIR / "board" / "node_modules")
    try:
        result = subprocess.run(
            ["bandit", "-r", scan_target, "-f", "json", "-q", "--exclude", exclude],
            capture_output=True, text=True, timeout=60
        )
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            print("❌ Bandit não retornou um JSON válido.")
            return {}
    except FileNotFoundError:
        print("⚠️ Bandit não instalado. Instale com 'pip install bandit' para testar.")
        return {}
    except Exception as e:
        print(f"❌ Erro ao rodar bandit SAST: {e}")
        return {}

def get_file_owner(file_path: str) -> str:
    """Consulta o file_registry.json para ver quem é o dono do arquivo. Fallback: Chen."""
    try:
        if FILE_REGISTRY.exists():
            data = json.loads(FILE_REGISTRY.read_text(encoding="utf-8"))
            reg = data.get("files", {})
            # Procura chave que termine com o nome do arquivo
            target_key = file_path.replace("\\", "/").lower()
            for key, val in reg.items():
                if key.lower().endswith(target_key) or target_key in key.lower():
                    return val.get("owner", "Chen")
    except Exception:
        pass
    return "Chen"

def apply_self_healing(issue: dict) -> bool:
    """Invoca o agente dono para corrigir a vulnerabilidade."""
    rel_path = issue.get("filename", "")
    # Converte para caminho relativo do repositório
    try:
        rel_path = str(Path(rel_path).relative_to(ROOT_DIR)).replace("\\", "/")
    except Exception:
        pass

    abs_path = ROOT_DIR / rel_path
    if not abs_path.exists():
        print(f"⚠️ Arquivo {rel_path} não encontrado no disco.")
        return False

    line_number = issue.get("line_number", 0)
    issue_text = issue.get("issue_text", "")
    severity = issue.get("issue_severity", "MEDIUM")

    print(f"\n🛠️ Consertando {rel_path} (Linha {line_number}) | Severidade: {severity}")
    print(f"   Problema: {issue_text}")

    # 1. Identifica o dono
    owner_name = get_file_owner(rel_path)
    print(f"   Dono do arquivo identificado: {owner_name}")
    owner = load_agent(owner_name)

    # 2. Lê o conteúdo do arquivo
    try:
        content = abs_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ Não foi possível ler o arquivo: {e}")
        return False

    # 3. Briefing para o agente
    prompt = (
        f"You are the owner of the file '{rel_path}'.\n"
        f"Bandit SAST reported a security vulnerability in this file:\n"
        f"- Line: {line_number}\n"
        f"- Severity: {severity}\n"
        f"- Bug details: {issue_text}\n\n"
        f"Here is the COMPLETE original file content:\n"
        f"```\n{content}\n```\n\n"
        f"Please rewrite this complete file to fix the vulnerability in line {line_number} while keeping all other original functionality completely intact. "
        f"Your response must consist ONLY of the complete new content of the file, starting directly with the code. "
        f"Do not write any markdown code block formatting (like ```python or ```) around the file contents. "
        f"Do not explain what you changed. Just output the complete raw file contents, and nothing else."
    )

    print(f"   Briefing {owner_name} para corrigir...")
    res = call_agent(owner, prompt)
    if not res["success"]:
        print(f"❌ Falha de IA ao tentar corrigir com {owner_name}: {res['error']}")
        return False

    fixed_code = res["content"].strip()

    # Limpeza de markdown caso o agente ignore a regra
    if fixed_code.startswith("```"):
        lines = fixed_code.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        fixed_code = "\n".join(lines).strip()

    # 4. Escreve de volta e valida
    try:
        abs_path.write_text(fixed_code, encoding="utf-8")
        print(f"✅ Arquivo {rel_path} atualizado com a correção!")
        # Atualiza file_registry
        update_file_registry([rel_path], owner, "RubberDuckFactory_SelfHealing")
        return True
    except Exception as e:
        print(f"❌ Não foi possível gravar o arquivo corrigido: {e}")
        return False

def main():
    print("=" * 60)
    print("🛡️  RubberDuckFactory -- Self-Healing Quality Gate Loop")
    print("=" * 60)

    # 1. Executa scan SAST
    print("🔍 Rodando varredura Bandit SAST no repositório...")
    scan_results = run_sast_scan()
    issues = scan_results.get("results", [])

    high_or_medium = [i for i in issues if i.get("issue_severity") in ("HIGH", "MEDIUM")]

    if not high_or_medium:
        print("✅ Nenhum problema de severidade ALTA ou MÉDIA encontrado! Quality gate aprovado.")
        sys.exit(0)

    print(f"⚠️ Encontrado(s) {len(high_or_medium)} problema(s) de severidade HIGH/MEDIUM.")

    # 2. Loop de auto-correção
    fixed_count = 0
    for issue in high_or_medium:
        success = apply_self_healing(issue)
        if success:
            fixed_count += 1

    print("\n" + "=" * 60)
    print(f"🔄 Re-escaneando para validar correções...")
    new_results = run_sast_scan()
    new_issues = new_results.get("results", [])
    new_high_or_medium = [i for i in new_issues if i.get("issue_severity") in ("HIGH", "MEDIUM")]

    if not new_high_or_medium:
        print("🎉 SUCESSO! Todos os problemas de segurança foram consertados e revalidados pelo SAST!")
    else:
        print(f"⚠️ Auto-correção parcial completa: {fixed_count} corrigidos. Ainda restam {len(new_high_or_medium)} problemas.")

    # Registra no histórico geral
    write_history({
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "type": "TASK_SUCCESS",
        "agent": "Orchestrator",
        "task": f"Self-healing loop completed. {fixed_count} security issues resolved. Remaining issues: {len(new_high_or_medium)}."
    })
    print("=" * 60)

if __name__ == "__main__":
    main()
