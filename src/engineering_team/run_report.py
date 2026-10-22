"""Run report: what each run cost, how long it took, and whether the quality gates passed.

After every run, write runs/<timestamp>/report.json and report.md, and copy the app
the crew built into runs/<timestamp>/app/, so earlier results survive the next
run's sandbox reset.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from .tools.sandbox_tools import SANDBOX_DIR

RUNS_DIR = SANDBOX_DIR.parent / "runs"

# USD per 1M tokens: (input, cached input, output). OpenAI list prices as of Oct 2026;
# check https://openai.com/api/pricing and update when they change.
PRICES = {
    "gpt-5.5": (5.00, 0.50, 30.00),
    "gpt-5.4-mini": (0.75, 0.075, 4.50),
}


def model_key(model: str) -> str:
    """'openai/gpt-5.5' -> 'gpt-5.5'."""
    return model.split("/")[-1]


def estimate_cost(model: str, prompt_tokens: int, cached_tokens: int, completion_tokens: int) -> float | None:
    """Estimated USD cost, or None for a model without a known price. Prompt tokens include cached ones."""
    prices = PRICES.get(model_key(model))
    if not prices:
        return None
    input_price, cached_price, output_price = prices
    uncached = max(prompt_tokens - cached_tokens, 0)
    return (uncached * input_price + cached_tokens * cached_price + completion_tokens * output_price) / 1_000_000


def agent_usage(agents) -> list[dict]:
    """Token usage and estimated cost for each agent, read from its LLM."""
    rows = []
    for agent in agents:
        llm = agent.llm
        model = getattr(llm, "model", str(llm))
        usage = llm.get_token_usage_summary() if hasattr(llm, "get_token_usage_summary") else None
        prompt = usage.prompt_tokens if usage else 0
        cached = usage.cached_prompt_tokens if usage else 0
        completion = usage.completion_tokens if usage else 0
        cost = estimate_cost(model, prompt, cached, completion)
        rows.append({
            "agent": agent.role.strip(),
            "model": model_key(model),
            "requests": usage.successful_requests if usage else 0,
            "prompt_tokens": prompt,
            "cached_tokens": cached,
            "completion_tokens": completion,
            "est_cost_usd": round(cost, 4) if cost is not None else None,
        })
    return rows


def build_report(requirements_file: str, started: datetime, finished: datetime, agents, gates: dict, error: str | None) -> dict:
    usage = agent_usage(agents)
    costs = [row["est_cost_usd"] for row in usage if row["est_cost_usd"] is not None]
    return {
        "requirements_file": requirements_file,
        "started": started.isoformat(timespec="seconds"),
        "duration_seconds": round((finished - started).total_seconds()),
        "status": "failed" if error else ("passed" if gates and all(g["passed"] for g in gates.values()) else "incomplete"),
        "error": error,
        "quality_gates": gates,
        "agents": usage,
        "total_tokens": sum(row["prompt_tokens"] + row["completion_tokens"] for row in usage),
        "total_est_cost_usd": round(sum(costs), 4),
    }


def to_markdown(report: dict) -> str:
    lines = [
        f"# Run report: {report['started']}",
        "",
        f"- **Requirements:** `{report['requirements_file']}`",
        f"- **Status:** {report['status']}",
        f"- **Duration:** {report['duration_seconds']} s",
        f"- **Total tokens:** {report['total_tokens']:,}",
        f"- **Estimated cost:** ${report['total_est_cost_usd']:.2f}",
    ]
    if report["error"]:
        lines.append(f"- **Error:** {report['error']}")
    lines += ["", "## Quality gates", "", "| Gate | Passed | Attempts | Detail |", "|---|---|---|---|"]
    for name, gate in report["quality_gates"].items():
        lines.append(f"| {name} | {'yes' if gate['passed'] else 'no'} | {gate['attempts']} | {gate['detail']} |")
    lines += ["", "## Agents", "", "| Agent | Model | Requests | Prompt tokens | Completion tokens | Est. cost |", "|---|---|---|---|---|---|"]
    for row in report["agents"]:
        cost = f"${row['est_cost_usd']:.4f}" if row["est_cost_usd"] is not None else "n/a"
        lines.append(f"| {row['agent']} | {row['model']} | {row['requests']} | {row['prompt_tokens']:,} | {row['completion_tokens']:,} | {cost} |")
    return "\n".join(lines) + "\n"


def save_report(report: dict, runs_dir: Path = RUNS_DIR) -> Path:
    """Write the report and a copy of the sandbox app; return the run folder."""
    run_dir = runs_dir / datetime.fromisoformat(report["started"]).strftime("%Y-%m-%d_%H-%M-%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (run_dir / "report.md").write_text(to_markdown(report), encoding="utf-8")
    if SANDBOX_DIR.exists():
        shutil.copytree(SANDBOX_DIR, run_dir / "app", ignore=shutil.ignore_patterns(".venv", "__pycache__"), dirs_exist_ok=True)
    return run_dir
