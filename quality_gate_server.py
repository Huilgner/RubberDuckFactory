"""
quality_gate_server.py — Servidor MCP do Comitê de Deploy
Ferramentas de validação pré-deploy para os agentes especialistas.

Roda no HOST (Windows Python), com acesso direto ao filesystem do projeto.
Registrado em .mcp.json como 'rubberduck-quality-gate' (transporte stdio).

Ferramentas disponíveis:
  - deploy_freeze(action)           → gerencia estado de Code Freeze
  - quality_gate_api_health()       → verifica saúde dos serviços Docker
  - quality_gate_infra_read()       → valida docker-compose.yaml
  - quality_gate_sast()             → análise estática de segurança (bandit)
  - quality_gate_log_scan()         → escaneia logs em busca de erros
  - deploy_verdict(reports)         → consolida relatórios e emite Go / No-Go
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

PROJECT_ROOT = Path(__file__).parent
FREEZE_FLAG = PROJECT_ROOT / ".code_freeze"

mcp = FastMCP(
    name="RubberDuckFactory Quality Gate",
    instructions="Ferramentas determinísticas de validação pré-deploy. Agentes fornecem raciocínio, estas tools provam factualmente.",
)

SEVERITY_RANK = {"OK": 0, "LEVE": 1, "MÉDIA": 2, "ALTA": 3, "CRÍTICA": 4}


# ─── Code Freeze ─────────────────────────────────────────────────────────────

@mcp.tool()
def deploy_freeze(action: str) -> dict:
    """
    Gerencia o estado de Code Freeze do repositório.

    Args:
        action: "set" para ativar freeze, "unset" para remover, "status" para consultar.

    Returns:
        dict com 'frozen' (bool), 'action' e 'since' (timestamp de ativação).
    """
    if action == "set":
        ts = datetime.now(timezone.utc).isoformat()
        FREEZE_FLAG.write_text(ts, encoding="utf-8")
        return {"frozen": True, "action": "set", "since": ts}
    elif action == "unset":
        if FREEZE_FLAG.exists():
            FREEZE_FLAG.unlink()
        return {"frozen": False, "action": "unset"}
    elif action == "status":
        frozen = FREEZE_FLAG.exists()
        return {
            "frozen": frozen,
            "since": FREEZE_FLAG.read_text(encoding="utf-8").strip() if frozen else None,
        }
    return {"error": f"action inválido: '{action}'. Use set, unset ou status."}


# ─── API Health ───────────────────────────────────────────────────────────────

@mcp.tool()
def quality_gate_api_health() -> dict:
    """
    Verifica a saúde dos serviços Docker da stack via HTTP.

    Returns:
        dict com status de cada serviço, alertas e severidade geral.
    """
    try:
        import httpx
    except ImportError:
        return {"error": "httpx não instalado. Execute: pip install httpx", "severity": "MÉDIA"}

    targets = {
        "board":      "http://localhost:3001",
        "mcp-server": "http://localhost:8001/mcp",
        "qdrant":     "http://localhost:6333/healthz",
    }

    results = {}
    alerts = []

    for name, url in targets.items():
        try:
            resp = httpx.get(url, timeout=5.0)
            ok = resp.status_code < 500
            results[name] = {"url": url, "status_code": resp.status_code, "ok": ok}
            if not ok:
                alerts.append({"service": name, "issue": f"HTTP {resp.status_code}", "severity": "ALTA"})
        except httpx.ConnectError:
            results[name] = {"url": url, "ok": False, "error": "serviço inacessível"}
            alerts.append({"service": name, "issue": "serviço não responde", "severity": "ALTA"})
        except Exception as e:
            results[name] = {"url": url, "ok": False, "error": str(e)}
            alerts.append({"service": name, "issue": str(e)[:80], "severity": "MÉDIA"})

    max_sev = max((SEVERITY_RANK.get(a["severity"], 0) for a in alerts), default=0)
    severity = next((k for k, v in SEVERITY_RANK.items() if v == max_sev), "OK")

    return {"services": results, "alerts": alerts, "severity": severity}


# ─── Infra Read ───────────────────────────────────────────────────────────────

@mcp.tool()
def quality_gate_infra_read() -> dict:
    """
    Lê e valida o docker-compose.yaml da stack.

    Returns:
        dict com serviços, ports expostos, healthchecks ausentes e severidade.
    """
    compose_path = PROJECT_ROOT / "docker-compose.yaml"
    if not compose_path.exists():
        return {"error": "docker-compose.yaml não encontrado", "severity": "CRÍTICA"}

    try:
        import yaml
        with open(compose_path, encoding="utf-8") as f:
            compose = yaml.safe_load(f)
    except ImportError:
        # fallback: leitura textual básica sem parse
        raw = compose_path.read_text(encoding="utf-8")
        return {
            "raw_preview": raw[:800],
            "warning": "pyyaml não instalado — análise estrutural indisponível. Execute: pip install pyyaml",
            "severity": "LEVE",
        }
    except Exception as e:
        return {"error": str(e), "severity": "CRÍTICA"}

    services = compose.get("services", {})
    alerts = []
    report = {}

    for name, svc in services.items():
        ports = svc.get("ports", [])
        has_healthcheck = "healthcheck" in svc
        restart = svc.get("restart", "no")
        env_vars = list(svc.get("environment", {}).keys() if isinstance(svc.get("environment"), dict)
                        else [e.split("=")[0] for e in svc.get("environment", [])])

        report[name] = {
            "ports": ports,
            "has_healthcheck": has_healthcheck,
            "restart_policy": restart,
            "env_vars": env_vars,
        }

        if not has_healthcheck:
            alerts.append({"service": name, "issue": "sem healthcheck definido", "severity": "MÉDIA"})
        if restart in ("no", None):
            alerts.append({"service": name, "issue": "restart policy ausente", "severity": "LEVE"})

    max_sev = max((SEVERITY_RANK.get(a["severity"], 0) for a in alerts), default=0)
    severity = next((k for k, v in SEVERITY_RANK.items() if v == max_sev), "OK")

    return {"services": report, "alerts": alerts, "severity": severity}


# ─── SAST ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def quality_gate_sast(target_path: str | None = None) -> dict:
    """
    Executa análise estática de segurança (SAST) nos arquivos Python.
    Requer bandit: pip install bandit

    Args:
        target_path: Caminho relativo a escanear (padrão: raiz do projeto).

    Returns:
        dict com issues por severidade, top issues e severidade geral.
    """
    scan_target = str(PROJECT_ROOT / (target_path or "."))
    exclude = str(PROJECT_ROOT / ".venv") + "," + str(PROJECT_ROOT / "board" / "node_modules")

    try:
        result = subprocess.run(
            ["bandit", "-r", scan_target, "-f", "json", "-q", "--exclude", exclude],
            capture_output=True, text=True, timeout=60,
        )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"error": "bandit não retornou JSON válido", "raw": result.stdout[:300], "severity": "MÉDIA"}

        results = data.get("results", [])
        high   = [r for r in results if r.get("issue_severity") == "HIGH"]
        medium = [r for r in results if r.get("issue_severity") == "MEDIUM"]
        low    = [r for r in results if r.get("issue_severity") == "LOW"]

        severity = "OK"
        if high:   severity = "ALTA"
        elif medium: severity = "MÉDIA"
        elif low:    severity = "LEVE"

        return {
            "total_issues": len(results),
            "high": len(high), "medium": len(medium), "low": len(low),
            "top_issues": [
                {
                    "file": r.get("filename", "").replace(str(PROJECT_ROOT), "").lstrip("/\\"),
                    "line": r.get("line_number"),
                    "issue": r.get("issue_text"),
                    "severity": r.get("issue_severity"),
                }
                for r in (high + medium)[:5]
            ],
            "severity": severity,
        }
    except FileNotFoundError:
        return {"error": "bandit não instalado. Execute: pip install bandit", "severity": "MÉDIA"}
    except subprocess.TimeoutExpired:
        return {"error": "timeout na análise SAST (>60s)", "severity": "MÉDIA"}


# ─── Log Scan ─────────────────────────────────────────────────────────────────

@mcp.tool()
def quality_gate_log_scan(lines: int = 500) -> dict:
    """
    Escaneia logs recentes do projeto em busca de padrões de erro.

    Args:
        lines: Número de linhas recentes a analisar por arquivo (padrão: 500).

    Returns:
        dict com contagem de achados por categoria, amostras e severidade.
    """
    log_sources = [
        PROJECT_ROOT / "project_ledger" / "hooks_audit.log",
        PROJECT_ROOT / "project_ledger" / "history.json",
    ]

    PATTERNS = {
        "CRÍTICA": [r"CRITICAL", r"FATAL", r"BLACKLIST", r"HALLUCINATION"],
        "ALTA":    [r"\bERROR\b", r"Exception", r"Traceback", r"\b500\b"],
        "MÉDIA":   [r"\bWARN(ING)?\b", r"deprecated", r"TASK_FAILURE"],
        "LEVE":    [r"timeout", r"retry", r"LEVE"],
    }

    findings: dict[str, list] = {sev: [] for sev in PATTERNS}

    for log_path in log_sources:
        if not log_path.exists():
            continue
        try:
            all_lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            for line in all_lines[-lines:]:
                for severity, pats in PATTERNS.items():
                    if any(re.search(p, line, re.IGNORECASE) for p in pats):
                        findings[severity].append({"source": log_path.name, "line": line[:120]})
                        break
        except Exception:
            pass

    max_sev = max((SEVERITY_RANK.get(k, 0) for k, v in findings.items() if v), default=0)
    severity = next((k for k, v in SEVERITY_RANK.items() if v == max_sev), "OK")

    return {
        "findings": {k: len(v) for k, v in findings.items()},
        "samples":  {k: v[:3] for k, v in findings.items() if v},
        "severity": severity,
    }


# ─── Veredito ─────────────────────────────────────────────────────────────────

@mcp.tool()
def deploy_verdict(reports: list[dict]) -> dict:
    """
    Consolida relatórios dos especialistas e emite o veredito de deploy.

    Args:
        reports: Lista de dicts com 'agent', 'scope' e 'severity' por especialista.

    Returns:
        dict com 'verdict' (GO | NO_GO), 'blockers', 'summary' e 'auto_deploy_authorized'.
    """
    BLOCK_THRESHOLD = SEVERITY_RANK["ALTA"]

    blockers = [r for r in reports if SEVERITY_RANK.get(r.get("severity", "OK"), 0) >= BLOCK_THRESHOLD]
    verdict = "NO_GO" if blockers else "GO"

    lines = []
    for r in reports:
        sev   = r.get("severity", "?")
        agent = r.get("agent", "?")
        scope = r.get("scope", "?")
        flag  = "BLOQUEIO" if SEVERITY_RANK.get(sev, 0) >= BLOCK_THRESHOLD else "APROVADO"
        lines.append(f"[{flag}] {agent} ({scope}): {sev}")

    return {
        "verdict": verdict,
        "blockers": blockers,
        "summary": "\n".join(lines),
        "auto_deploy_authorized": verdict == "GO",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
