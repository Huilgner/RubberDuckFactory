"""agent_runner: validação de artefatos, DSL, contexto de arquivos e seleção de juiz."""
import json

import pytest

import agent_runner
from agent_runner import build_files_context, parse_and_execute_dsl, validate_artifacts


@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """Redireciona a raiz do projeto para um sandbox."""
    monkeypatch.setattr(agent_runner, "ROOT_DIR", tmp_path)
    return tmp_path


def test_validate_artifacts_ok_and_skip(project_root):
    (project_root / "good.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (project_root / "good.json").write_text('{"a": 1}', encoding="utf-8")
    (project_root / "note.txt").write_text("qualquer coisa", encoding="utf-8")

    all_ok, results = validate_artifacts(["good.py", "good.json", "note.txt"])
    assert all_ok
    assert {r["file"]: r["status"] for r in results} == {
        "good.py": "ok", "good.json": "ok", "note.txt": "skipped",
    }


def test_validate_artifacts_fails_on_bad_syntax(project_root):
    (project_root / "bad.py").write_text("def f(:\n    return 1\n", encoding="utf-8")
    (project_root / "bad.json").write_text('{"a": 1,}', encoding="utf-8")

    all_ok, results = validate_artifacts(["bad.py", "bad.json"])
    assert not all_ok
    assert all(r["status"] == "fail" for r in results)


def test_dsl_writes_files_and_blocks_traversal(project_root):
    dsl = (
        "[FILE: ../evil.txt]\n[CONTENT]\npwned\n[END_CONTENT]\n"
        "[FILE: sub/inside.txt]\n[CONTENT]\nok\n[END_CONTENT]"
    )
    written = parse_and_execute_dsl(dsl)
    assert written == ["sub/inside.txt"]
    assert (project_root / "sub" / "inside.txt").read_text(encoding="utf-8") == "ok"
    assert not (project_root.parent / "evil.txt").exists()


def test_build_files_context_injects_and_caps(project_root):
    (project_root / "a.py").write_text("CONTEUDO_A = 1\n", encoding="utf-8")
    (project_root / "grande.txt").write_text("x" * 50_000, encoding="utf-8")

    ctx = build_files_context(["a.py", "inexistente.py", "../fora.txt"])
    assert "CONTEUDO_A" in ctx
    assert "inexistente" not in ctx and "fora.txt" not in ctx

    ctx2 = build_files_context(["grande.txt"])
    assert len(ctx2) < agent_runner.MAX_CONTEXT_PER_FILE + 500
    assert "(TRUNCADO)" in ctx2

    assert build_files_context(None) == ""
    assert build_files_context([]) == ""


def test_judge_family_never_matches_competitors():
    from duel_runner import JUDGE_CANDIDATES, pick_judge_model

    j = pick_judge_model([{"model": "google/gemini-2.5-flash"},
                          {"model": "deepseek/deepseek-v4-flash"}])
    assert j.split("/")[0] not in {"google", "deepseek"}

    # todos os candidatos conflitam -> usa o preferido mesmo assim
    all_families = [{"model": c} for c in JUDGE_CANDIDATES]
    assert pick_judge_model(all_families) == JUDGE_CANDIDATES[0]


def test_evolution_uses_rolling_window(project_root, sandbox_ledger, monkeypatch):
    monkeypatch.setattr(agent_runner, "LEDGER_DIR", sandbox_ledger)
    agent_file = project_root / "dummy.json"
    agent_file.write_text(json.dumps({
        "nome": "Dummy", "tier": 2, "model": "x", "evolution": "Stable",
        "success_rate": 100.0, "tasks_completed": 200, "tasks_failed": 0,
        "recent_results": [1] * 14,
    }), encoding="utf-8")

    # 6 falhas seguidas: janela = 14 acertos + 6 falhas = 70% -> Mutating,
    # mesmo com success_rate vitalicio ~97%
    for _ in range(6):
        agent_runner.update_agent_stats({"_file": str(agent_file)}, False)

    d = json.loads(agent_file.read_text(encoding="utf-8"))
    assert d["evolution"] == "Mutating"
    assert d["success_rate"] > 95.0  # vitalicio quase intacto; a janela decidiu
