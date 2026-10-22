# Engineering Team

A [CrewAI](https://crewai.com) crew of four AI engineers that takes plain-English requirements and
designs, codes, tests and builds a UI for a working Python app, all on its own.

Out of the box, the requirements in `src/engineering_team/main.py` ask for an **account management
system for a trading simulation**: deposits, withdrawals, buying and selling shares, portfolio value
and profit/loss.

## The crew

| Agent | Model | Job |
|---|---|---|
| Engineering Lead | `gpt-5.5` | Turns the requirements into a design (`design.md`), checking the latest Gradio APIs through the Context7 MCP server |
| Backend Engineer | `gpt-5.4-mini` | Writes the Python backend module |
| Frontend Engineer | `gpt-5.4-mini` | Writes a Gradio UI (`app.py`) and a script that checks it builds |
| Test Engineer | `gpt-5.4-mini` | Writes `unittest` tests, runs them, and fixes defects until they pass |

The agents run sequentially and share a `sandbox/` folder through custom tools
(`src/engineering_team/tools/sandbox_tools.py`). Any code they run executes inside a throwaway
**Docker** container, not on your machine.

`src/engineering_team/patch.py` works around a CrewAI 1.14.4 bug that made MCP tools with hyphens
in their names unreachable.

## Quality gates and run reports

My addition to the course project. An agent saying "all tests pass" isn't proof, so the crew now checks
its own work and reports what each run cost.

- **Quality gates** (`src/engineering_team/quality_gate.py`): CrewAI task guardrails that run the code
  themselves in the same Docker sandbox. The test task only completes once
  `python -m unittest discover` finds tests and they all pass. The frontend task only completes once the
  Gradio app builds. On failure, the task goes back to the agent with the real error output (up to 3 retries).
- **Run reports** (`src/engineering_team/run_report.py`): every run writes `runs/<timestamp>/report.md` and
  `report.json`, covering status, duration, gate attempts, and tokens and estimated cost per agent
  (from OpenAI list prices in `PRICES`). It also saves a copy of the app the crew built, so earlier runs
  survive the next sandbox reset.
- **Requirements as files** (`requirements/`): pick a spec by name, with no code changes. Three are included:
  `trading_account`, `expense_tracker` and `inventory_manager`.
- **Tests**: a pytest suite for the gates, cost maths, reports and requirements loading. It needs no
  Docker or API key.

## Example output

`example_output/` holds the app the crew built on one run: the design, backend, Gradio UI, unit
tests and test summary. (`sandbox/` is wiped at the start of every run, so this copy is kept separately.)

## Setup

Prerequisites: [uv](https://docs.astral.sh/uv/), Python 3.10 to 3.13, and
[Docker](https://www.docker.com/) running.

```bash
uv sync
cp .env.example .env   # then add your OpenAI API key
```

## Run

```bash
uv run run_crew                    # builds requirements/trading_account.md
uv run run_crew expense_tracker    # or any spec in requirements/, or a path to your own .md file
```

This resets `sandbox/`, runs the crew, prints the run report and saves it under `runs/`. When it finishes,
try the app it built:

```bash
cd sandbox
uv run app.py
```

Run the tests with:

```bash
uv run pytest tests
```

## Credits

Based on the CrewAI week of Ed Donner's [Agents course](https://github.com/ed-donner/agents) (MIT License).
