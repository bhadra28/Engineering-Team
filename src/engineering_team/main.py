#!/usr/bin/env python
import sys
import warnings

from datetime import datetime
from pathlib import Path

import engineering_team.patch  # noqa: F401 — applies CrewAI MCP monkey-patch on import
from engineering_team.crew import EngineeringTeam
from .tools.sandbox_tools import reset_sandbox
from .quality_gate import gate_results, reset_gate_results
from .run_report import build_report, save_report, to_markdown
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Requirements live in markdown files, so the crew can build something new without code changes:
#   uv run run_crew                      -> requirements/trading_account.md
#   uv run run_crew expense_tracker      -> requirements/expense_tracker.md
#   uv run run_crew path/to/my_spec.md   -> any file
REQUIREMENTS_DIR = Path(__file__).parents[2] / "requirements"
DEFAULT_REQUIREMENTS = "trading_account"


def resolve_requirements(arg: str | None) -> Path:
    """Find a requirements file from a path, or a name in the requirements folder."""
    name = arg or DEFAULT_REQUIREMENTS
    for candidate in (Path(name), REQUIREMENTS_DIR / name, REQUIREMENTS_DIR / f"{name}.md"):
        if candidate.is_file():
            return candidate
    available = ", ".join(sorted(p.stem for p in REQUIREMENTS_DIR.glob("*.md")))
    raise FileNotFoundError(f"No requirements file '{name}'. Available: {available}")


def run():
    """
    Run the crew on a requirements file, then save a run report and a copy of the app it built.
    """
    path = resolve_requirements(sys.argv[1] if len(sys.argv) > 1 else None)
    inputs = {
        'requirements': path.read_text(encoding="utf-8")
    }

    reset_sandbox() #fresh start each time we run the crew
    reset_gate_results()
    crew = EngineeringTeam().crew()
    started, error = datetime.now(), None
    try:
        crew.kickoff(inputs=inputs)
    except Exception as e:
        error = str(e)
    finally:
        report = build_report(path.name, started, datetime.now(), crew.agents, dict(gate_results), error)
        run_dir = save_report(report)
        print(to_markdown(report))
        print(f"Run report and app saved to {run_dir}")
    if error:
        raise Exception(f"An error occurred while running the crew: {error}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "AI LLMs",
        'current_year': str(datetime.now().year)
    }
    try:
        EngineeringTeam().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        EngineeringTeam().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "AI LLMs",
        "current_year": str(datetime.now().year)
    }

    try:
        EngineeringTeam().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

def run_with_trigger():
    """
    Run the crew with trigger payload.
    """
    import json

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "topic": "",
        "current_year": ""
    }

    try:
        result = EngineeringTeam().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")
