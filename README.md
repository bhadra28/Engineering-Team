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
uv run run_crew
```

This resets `sandbox/` and runs the crew. When it finishes, try the app it built:

```bash
cd sandbox
uv run app.py
```

To build something different, edit the `requirements` text in `src/engineering_team/main.py`.

## Credits

Based on the CrewAI week of Ed Donner's [Agents course](https://github.com/ed-donner/agents) (MIT License).
