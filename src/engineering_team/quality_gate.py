"""Quality gates: CrewAI task guardrails that check the agents' work by running it.

An agent saying "all tests pass" is not proof. After the test and frontend tasks
finish, these guardrails run the code themselves in the same Docker sandbox. If
the check fails, CrewAI sends the task back to the agent with the failure output
as feedback, up to the task's guardrail_max_retries.

Each gate records its attempts in `gate_results`, which the run report reads.
"""

import re
import subprocess
from typing import Any

from crewai import TaskOutput

from .tools.sandbox_tools import SANDBOX_DIR, docker_uv_run

FEEDBACK_CHARS = 3000  # how much failing output to hand back to the agent

gate_results: dict[str, dict] = {}


def reset_gate_results() -> None:
    gate_results.clear()


def _record(gate: str, passed: bool, detail: str) -> None:
    result = gate_results.setdefault(gate, {"attempts": 0, "passed": False, "detail": ""})
    result["attempts"] += 1
    result["passed"] = passed
    result["detail"] = detail


def _run(args: list[str]) -> tuple[int, str]:
    """Run in the sandbox; return the exit code and combined output (unittest reports on stderr)."""
    try:
        result = docker_uv_run(args)
    except subprocess.TimeoutExpired:
        return 1, "Timed out after 300 seconds."
    except FileNotFoundError:
        return 1, "Docker is not available. Start Docker and try again."
    return result.returncode, f"{result.stdout}\n{result.stderr}".strip()


def parse_unittest(output: str) -> tuple[int, bool]:
    """Return (tests run, all passed) from unittest's summary lines."""
    ran = re.search(r"^Ran (\d+) tests?", output, re.MULTILINE)
    count = int(ran.group(1)) if ran else 0
    passed = count > 0 and re.search(r"^OK\b", output, re.MULTILINE) is not None
    return count, passed


def unit_tests_gate(output: TaskOutput) -> tuple[bool, Any]:
    """Pass only if the sandbox's unit tests are found and all of them pass."""
    code, log = _run(["python", "-m", "unittest", "discover", "-p", "test_*.py", "-v"])
    count, passed = parse_unittest(log)
    if code == 0 and passed:
        _record("unit_tests", True, f"{count} tests passed")
        return True, output.raw
    reason = "no tests were found (name the file test_*.py)" if count == 0 else f"{count} tests ran but not all passed"
    _record("unit_tests", False, reason)
    return False, (
        f"Quality gate failed: {reason}. I ran `python -m unittest discover -p 'test_*.py'` in the sandbox. "
        f"Fix the backend or the tests, run them again, and only finish when they all pass.\n\n"
        f"Output:\n{log[-FEEDBACK_CHARS:]}"
    )


def ui_builds_gate(output: TaskOutput) -> tuple[bool, Any]:
    """Pass only if app.py exists and the frontend's validation script (or a plain import) succeeds."""
    if not (SANDBOX_DIR / "app.py").is_file():
        _record("ui_builds", False, "app.py missing")
        return False, "Quality gate failed: app.py was not found in the sandbox. Write the Gradio UI to app.py."
    validators = sorted(p.name for p in SANDBOX_DIR.glob("_validate*.py"))
    args = [validators[0]] if validators else ["python", "-c", "import app"]
    code, log = _run(args)
    if code == 0:
        _record("ui_builds", True, f"{' '.join(args)} succeeded")
        return True, output.raw
    _record("ui_builds", False, f"{' '.join(args)} failed")
    return False, (
        f"Quality gate failed: running `{' '.join(args)}` in the sandbox exited with code {code}. "
        f"Fix app.py so the Gradio Blocks construct without error.\n\nOutput:\n{log[-FEEDBACK_CHARS:]}"
    )
