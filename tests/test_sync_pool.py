"""sync_pool: sanitização, seed, bootstrap e update preservando stats locais."""
import json

import pytest

import sync_pool


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    active = tmp_path / "active"
    pool = tmp_path / "pool"
    active.mkdir()
    monkeypatch.setattr(sync_pool, "ACTIVE_DIR", active)
    monkeypatch.setattr(sync_pool, "POOL_DIR", pool)
    return active, pool


AGENT = {
    "nome": "Chen", "tier": 2, "specialty": "Backend", "model": "deepseek/deepseek-chat",
    "ruleset_version": "v2", "status": "active", "evolution": "Mutating",
    "success_rate": 77.5, "tasks_completed": 31, "tasks_failed": 9,
    "pontos": {"externos": 12, "internos": 4},
}


def test_sanitize_strips_local_state():
    clean = sync_pool.sanitize(AGENT)
    assert clean["model"] == "deepseek/deepseek-chat" and clean["tier"] == 2
    assert clean["tasks_completed"] == 0 and clean["success_rate"] == 100.0
    assert clean["evolution"] == "Stable"
    assert clean["pontos"] == {"externos": 0, "internos": 0}


def test_seed_bootstrap_roundtrip(dirs):
    active, pool = dirs
    (active / "chen.json").write_text(json.dumps(AGENT), encoding="utf-8")

    sync_pool.seed_pool()
    assert json.loads((pool / "chen.json").read_text(encoding="utf-8"))["tasks_completed"] == 0

    # clone novo: active vazio -> bootstrap recria a partir do pool
    (active / "chen.json").unlink()
    sync_pool.bootstrap()
    boot = json.loads((active / "chen.json").read_text(encoding="utf-8"))
    assert boot["model"] == AGENT["model"] and boot["tasks_completed"] == 0


def test_update_pulls_definition_preserving_stats(dirs):
    active, pool = dirs
    (active / "chen.json").write_text(json.dumps(AGENT), encoding="utf-8")
    sync_pool.seed_pool()

    # o pool evolui: modelo trocado via PR
    pool_def = json.loads((pool / "chen.json").read_text(encoding="utf-8"))
    pool_def["model"] = "deepseek/deepseek-v4-pro"
    (pool / "chen.json").write_text(json.dumps(pool_def), encoding="utf-8")

    sync_pool.update()
    local = json.loads((active / "chen.json").read_text(encoding="utf-8"))
    assert local["model"] == "deepseek/deepseek-v4-pro"      # definição atualizada
    assert local["tasks_completed"] == 31                     # stats locais intactos
    assert local["evolution"] == "Mutating"
