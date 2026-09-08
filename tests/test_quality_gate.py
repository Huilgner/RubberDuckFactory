"""quality_gate_server: ADR-004 fase 1 — veredito persistido, dívida acumulada e freeze acoplado."""
import json

import pytest

pytest.importorskip("mcp", reason="mcp não instalado (host precisa de: pip install mcp)")

import quality_gate_server as qg


@pytest.fixture
def gate(sandbox_ledger, monkeypatch):
    monkeypatch.setattr(qg, "FREEZE_FLAG", sandbox_ledger / ".code_freeze")
    monkeypatch.setattr(qg, "LAST_VERDICT", sandbox_ledger / "last_verdict.json")
    freeze = qg.deploy_freeze.fn if hasattr(qg.deploy_freeze, "fn") else qg.deploy_freeze
    verdict = qg.deploy_verdict.fn if hasattr(qg.deploy_verdict, "fn") else qg.deploy_verdict
    return freeze, verdict


def test_unset_denied_without_go(gate):
    freeze, _ = gate
    freeze("set")
    r = freeze("unset")
    assert r.get("error") and r["frozen"] is True


def test_three_media_findings_block(gate):
    freeze, verdict = gate
    freeze("set")
    v = verdict([{"agent": a, "scope": "x", "severity": "MÉDIA"}
                 for a in ("Shadow", "Atlas", "Lens")], "teste")
    assert v["verdict"] == "NO_GO" and v["media_findings"] == 3
    assert freeze("unset").get("error")


def test_go_after_freeze_unlocks(gate):
    freeze, verdict = gate
    freeze("set")
    v = verdict([{"agent": "Shadow", "scope": "sast", "severity": "OK"}], "teste")
    assert v["verdict"] == "GO"
    r = freeze("unset")
    assert r["frozen"] is False and r.get("authorized_by_verdict")


def test_override_requires_reason_and_audits(gate, sandbox_ledger):
    import ledger_io
    freeze, _ = gate
    freeze("set")
    assert freeze("override").get("error")
    r = freeze("override", reason="hotfix aprovado pelo Arquiteto")
    assert r["frozen"] is False and r["audited"]
    types = {e["type"] for e in ledger_io.read_history()}
    assert "FREEZE_OVERRIDE" in types


def test_verdict_persisted_in_ledger(gate):
    import ledger_io
    _, verdict = gate
    verdict([{"agent": "Lens", "scope": "qa", "severity": "ALTA"}], "meu_projeto")
    events = [e for e in ledger_io.read_history() if e["type"] == "DEPLOY_VERDICT"]
    assert events and events[-1]["verdict"] == "NO_GO" and events[-1]["project"] == "meu_projeto"


# ─── Guard do destravamento: comparacao de timestamps ────────────────────────
# Regressoes fixadas depois do bug de 2026-09-08: o guard usava
# `verdict_ts <= frozen_since` e negava um GO emitido no mesmo tique do relogio.

def _monta_estado(sandbox_ledger, freeze_ts: str, verdict_ts: str, verdict: str = "GO") -> None:
    """Escreve freeze e ultimo veredito com timestamps controlados."""
    (sandbox_ledger / ".code_freeze").write_text(freeze_ts, encoding="utf-8")
    (sandbox_ledger / "last_verdict.json").write_text(
        json.dumps({"verdict": verdict, "timestamp": verdict_ts, "project": "teste"}),
        encoding="utf-8",
    )


def test_empate_de_timestamp_destrava(gate, sandbox_ledger):
    """~15,6 ms de granularidade no Windows fazem freeze e verdict empatarem."""
    freeze, _ = gate
    ts = "2026-09-08T17:04:37.791433+00:00"
    _monta_estado(sandbox_ledger, freeze_ts=ts, verdict_ts=ts)
    r = freeze("unset")
    assert r["frozen"] is False and r["authorized_by_verdict"] == ts


def test_veredito_anterior_ao_freeze_nao_destrava(gate, sandbox_ledger):
    """A intencao do ADR-004 continua valendo: GO velho nao destrava freeze novo."""
    freeze, _ = gate
    _monta_estado(
        sandbox_ledger,
        freeze_ts="2026-09-08T17:04:37.791433+00:00",
        verdict_ts="2026-09-08T17:04:30.000000+00:00",
    )
    assert freeze("unset").get("error")


def test_offset_em_formato_diferente_nao_engana_o_guard(gate, sandbox_ledger):
    """Sufixo 'Z' e '+00:00' sao o mesmo instante — comparacao textual erraria."""
    freeze, _ = gate
    _monta_estado(
        sandbox_ledger,
        freeze_ts="2026-09-08T17:04:37+00:00",
        verdict_ts="2026-09-08T17:04:38Z",
    )
    r = freeze("unset")
    assert r["frozen"] is False


def test_timestamp_corrompido_nega_destravamento(gate, sandbox_ledger):
    """Sem prova valida, o freeze so sai por override auditado."""
    freeze, _ = gate
    _monta_estado(
        sandbox_ledger,
        freeze_ts="2026-09-08T17:04:37+00:00",
        verdict_ts="nao-e-um-timestamp",
    )
    assert freeze("unset").get("error")
