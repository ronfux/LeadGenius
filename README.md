# Market Research Agent (Gemini CLI)

Automate large-scale business discovery with a manager/worker pipeline. This project uses a planning agent to generate city-level research tasks and a pool of worker agents to execute web searches in parallel, then aggregates and deduplicates results into CSV/JSON outputs.

## How it works

1. **Manager** generates a task list (city + search terms + fields).
2. **Workers** run those tasks in parallel via the Gemini CLI with web search enabled.
3. **Aggregator** merges outputs, removes duplicates, and exports results.

## Requirements

- Python 3.9+
- Gemini CLI installed and authenticated (binary named `gemini` available on PATH)
- Internet access for worker searches

## Install

```bash
pip install -r requirements.txt
```

Verify the CLI is available:

```bash
python main.py check
```

## Quick start

Run a research job:

```bash
python main.py research --target config/targets/example.yaml --states TX,CA
```

Adjust worker concurrency:

```bash
python main.py research --target config/targets/example.yaml --states TX,CA --workers 20
```

Skip aggregation (run it later):

```bash
python main.py research --target config/targets/example.yaml --states TX --skip-aggregate
python main.py aggregate
```

## Create a new target

Generate a new industry config:

```bash
python main.py init-target --industry "Plumbing" --target config/targets/plumbing.yaml
```

Or copy and edit `config/targets/example.yaml`.

## Outputs

- Raw worker results: `data/outputs/`
- Aggregated results: `data/aggregated/results.json` and `data/aggregated/results.csv`

## Configuration

Global settings live in `config/settings.yaml`:

- `models.manager` / `models.worker`: model IDs passed to the Gemini CLI
- `parallelism.max_workers`: number of concurrent workers
- `parallelism.spawn_delay`: delay between worker starts
- `output.formats`: `json`, `csv`, or both
- `paths.outputs` / `output.directory`: raw and aggregated output locations

Note: models must be supported by your installed Gemini CLI. Use `python main.py check` to see available models.

## Project layout

```
market-research-agent/
├── main.py
├── config/
│   ├── settings.yaml
│   └── targets/
├── sops/
│   ├── manager/
│   └── worker/
├── src/
│   ├── orchestrator.py
│   ├── worker_pool.py
│   ├── aggregator.py
│   └── cli_adapters/
└── data/
    ├── outputs/
    └── aggregated/
```

## Notes

- Workers run with web search enabled by prepending `@web` to prompts.
- Output schemas are defined by SOPs in `sops/`.
- The aggregator expects JSON outputs that follow those SOP schemas.
