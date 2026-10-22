import pytest
from crewai import TaskOutput

from engineering_team import quality_gate
from engineering_team.quality_gate import gate_results, parse_unittest, reset_gate_results, unit_tests_gate, ui_builds_gate

OK_LOG = "test_deposit ... ok\n\n----------------------------------------------------------------------\nRan 32 tests in 0.004s\n\nOK"
FAIL_LOG = "test_withdraw ... FAIL\n\nRan 5 tests in 0.002s\n\nFAILED (failures=1)"


@pytest.fixture(autouse=True)
def clean_results():
    reset_gate_results()


def output():
    return TaskOutput(description="task", agent="Test Engineer", raw="All tests pass!")


def fake_run(monkeypatch, code, log):
    calls = []
    monkeypatch.setattr(quality_gate, "_run", lambda args: (calls.append(args), (code, log))[1])
    return calls


def test_parse_unittest_summary():
    assert parse_unittest(OK_LOG) == (32, True)
    assert parse_unittest(FAIL_LOG) == (5, False)
    assert parse_unittest("NO TESTS RAN") == (0, False)


def test_tests_gate_passes_when_tests_pass(monkeypatch):
    fake_run(monkeypatch, 0, OK_LOG)
    passed, result = unit_tests_gate(output())
    assert passed and result == "All tests pass!"
    assert gate_results["unit_tests"] == {"attempts": 1, "passed": True, "detail": "32 tests passed"}


def test_tests_gate_rejects_the_agents_claim_when_tests_fail(monkeypatch):
    fake_run(monkeypatch, 1, FAIL_LOG)
    passed, feedback = unit_tests_gate(output())
    assert not passed
    assert "5 tests ran but not all passed" in feedback
    assert "FAILED (failures=1)" in feedback  # the agent sees the real failure output


def test_tests_gate_fails_when_no_tests_exist(monkeypatch):
    fake_run(monkeypatch, 5, "Ran 0 tests in 0.000s\n\nNO TESTS RAN")
    passed, feedback = unit_tests_gate(output())
    assert not passed and "no tests were found" in feedback


def test_attempts_accumulate_across_retries(monkeypatch):
    fake_run(monkeypatch, 1, FAIL_LOG)
    unit_tests_gate(output())
    fake_run(monkeypatch, 0, OK_LOG)
    unit_tests_gate(output())
    assert gate_results["unit_tests"]["attempts"] == 2
    assert gate_results["unit_tests"]["passed"] is True


def test_ui_gate_needs_app_py(monkeypatch, tmp_path):
    monkeypatch.setattr(quality_gate, "SANDBOX_DIR", tmp_path)
    passed, feedback = ui_builds_gate(output())
    assert not passed and "app.py" in feedback


def test_ui_gate_prefers_the_validation_script(monkeypatch, tmp_path):
    (tmp_path / "app.py").write_text("import gradio")
    (tmp_path / "_validate.py").write_text("import app")
    monkeypatch.setattr(quality_gate, "SANDBOX_DIR", tmp_path)
    calls = fake_run(monkeypatch, 0, "Blocks constructed successfully")
    passed, _ = ui_builds_gate(output())
    assert passed and calls == [["_validate.py"]]


def test_ui_gate_falls_back_to_import(monkeypatch, tmp_path):
    (tmp_path / "app.py").write_text("import gradio")
    monkeypatch.setattr(quality_gate, "SANDBOX_DIR", tmp_path)
    calls = fake_run(monkeypatch, 1, "ModuleNotFoundError: No module named 'backend'")
    passed, feedback = ui_builds_gate(output())
    assert not passed and calls == [["python", "-c", "import app"]]
    assert "ModuleNotFoundError" in feedback
