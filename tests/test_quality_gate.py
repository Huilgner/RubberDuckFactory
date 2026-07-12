"""quality_gate_server: ADR-004 fase 1 — veredito persistido, dívida acumulada e freeze acoplado."""
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
