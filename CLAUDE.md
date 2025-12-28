# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Check if Gemini CLI is available
python main.py check

# Run research for specific states
python main.py research --target config/targets/example.yaml --states TX,CA

# Run with custom worker count
python main.py research --target config/targets/example.yaml --states TX --workers 20

# Aggregate results only (after research)
python main.py aggregate

# Create new industry target config
python main.py init-target --industry "Plumbing" --target config/targets/plumbing.yaml
```

## Architecture

This is a **Manager/Worker agentic system** for automated market research using Gemini CLI.

### Three-Phase Workflow

1. **Manager Phase** (`Orchestrator.run_manager`): Uses Gemini Pro to analyze the research request and generate a JSON array of city-level search tasks
2. **Worker Phase** (`WorkerPool.execute_tasks`): Executes tasks in parallel via `ThreadPoolExecutor`, each spawning a Gemini CLI subprocess
3. **Aggregation Phase** (`Aggregator.aggregate`): Combines worker outputs, deduplicates by company name + location, exports to JSON/CSV

### Key Components

- **`src/orchestrator.py`**: Main coordinator - loads config, runs manager, distributes to workers, triggers aggregation
- **`src/worker_pool.py`**: `ThreadPoolExecutor`-based parallel execution with rate limiting (`spawn_delay`)
- **`src/cli_adapters/`**: Abstract adapter pattern for CLI backends (currently Gemini, extensible to Claude)
- **`sops/`**: Markdown "Standard Operating Procedures" that define agent behavior via prompts

### Data Flow

```
Target Config (YAML) → Manager (Gemini Pro) → Task List (JSON)
                                                    ↓
                                    Worker Pool (Gemini Flash × N)
                                                    ↓
                              data/outputs/*.json → Aggregator → data/aggregated/
```

### Configuration

- **`config/settings.yaml`**: Models, parallelism settings, paths
- **`config/targets/*.yaml`**: Industry-specific configs (search terms, data fields)
- Models are configured separately: `manager` (Pro for reasoning) and `worker` (Flash for speed)

### Adding a New CLI Backend

1. Create adapter in `src/cli_adapters/` extending `CLIAdapter` base class
2. Implement `execute()`, `get_available_models()`, `is_available()`
3. Update `Orchestrator._create_adapter()` to support the new CLI type
