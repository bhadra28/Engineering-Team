import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from engineering_team import run_report
from engineering_team.main import resolve_requirements
from engineering_team.run_report import build_report, estimate_cost, save_report, to_markdown


def fake_agent(role, model, prompt, cached, completion, requests=3):
    usage = SimpleNamespace(prompt_tokens=prompt, cached_prompt_tokens=cached, completion_tokens=completion, successful_requests=requests)
    llm = SimpleNamespace(model=model, get_token_usage_summary=lambda: usage)
    return SimpleNamespace(role=f"{role}\n", llm=llm)


AGENTS = [
    fake_agent("Engineering Lead", "openai/gpt-5.5", 100_000, 20_000, 10_000),
    fake_agent("Backend Engineer", "gpt-5.4-mini", 200_000, 0, 40_000),
]
GATES = {"unit_tests": {"attempts": 2, "passed": True, "detail": "32 tests passed"}}
START = datetime(2026, 10, 22, 9, 0, 0)


def test_estimate_cost_charges_cached_tokens_at_the_cached_rate():
    # 80k uncached * $5 + 20k cached * $0.50 + 10k output * $30, per 1M tokens
    assert estimate_cost("openai/gpt-5.5", 100_000, 20_000, 10_000) == pytest.approx(0.40 + 0.01 + 0.30)


def test_unknown_model_has_no_cost():
    assert estimate_cost("some-other-model", 1000, 0, 1000) is None


def test_report_totals_and_status():
    report = build_report("trading_account.md", START, START + timedelta(minutes=7), AGENTS, GATES, None)
    assert report["status"] == "passed"
    assert report["duration_seconds"] == 420
    assert report["total_tokens"] == 350_000
    assert report["agents"][0]["agent"] == "Engineering Lead"
    # Lead $0.71 plus backend: 200k * $0.75 + 40k * $4.50 per 1M = $0.33
    assert report["total_est_cost_usd"] == pytest.approx(1.04)


def test_failed_run_is_reported_as_failed():
    report = build_report("x.md", START, START, AGENTS, {}, "boom")
    assert report["status"] == "failed" and report["error"] == "boom"


def test_report_saves_json_markdown_and_a_copy_of_the_app(monkeypatch, tmp_path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    (sandbox / "app.py").write_text("print('hi')")
    (sandbox / ".venv").mkdir()
    monkeypatch.setattr(run_report, "SANDBOX_DIR", sandbox)
    report = build_report("trading_account.md", START, START, AGENTS, GATES, None)
    run_dir = save_report(report, runs_dir=tmp_path / "runs")
    assert json.loads((run_dir / "report.json").read_text())["status"] == "passed"
    assert "| unit_tests | yes | 2 |" in (run_dir / "report.md").read_text()
    assert (run_dir / "app" / "app.py").is_file()
    assert not (run_dir / "app" / ".venv").exists()


def test_markdown_shows_costs():
    md = to_markdown(build_report("a.md", START, START, AGENTS, GATES, None))
    assert "Estimated cost:** $1.04" in md


def test_requirements_resolve_by_name_and_reject_unknown():
    assert resolve_requirements(None).name == "trading_account.md"
    assert resolve_requirements("expense_tracker").name == "expense_tracker.md"
    with pytest.raises(FileNotFoundError, match="inventory_manager"):
        resolve_requirements("does_not_exist")
