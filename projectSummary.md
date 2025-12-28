# Market Research AI Employee - Project Summary

## What Is This?

The **Market Research AI Employee** is an automated system that finds and collects information about businesses across the United States. Instead of manually searching Google for companies in every city, this tool does it automatically — and it can search hundreds of cities simultaneously.

Think of it like having a team of research assistants who never sleep, never get tired, and can all work at the same time.

---

## The Problem It Solves

Imagine you're trying to find every ambulance company in Texas. You'd have to:

1. Search "ambulance company Houston"
2. Write down all the companies you find
3. Search "ambulance company Dallas"
4. Write down those companies
5. Repeat for Austin, San Antonio, Fort Worth, El Paso...
6. Then do the same for every other state

This could take weeks of manual work. Our AI Employee does this in minutes.

---

## How It Works: The Manager/Worker Model

The system uses two types of AI agents working together:

### 🧠 The Manager (The Strategist)
- Uses a smarter, more expensive AI model (Gemini Pro)
- Receives your research request (e.g., "Find EMS companies in Texas and California")
- Creates a detailed plan: which cities to search, what terms to use
- Outputs a list of specific tasks for the workers

### 🐝 The Workers (The Doers)
- Use a faster, cheaper AI model (Gemini Flash)
- Each worker takes one task (e.g., "Search for ambulance companies in Houston, TX")
- Searches the web and extracts business information
- Returns structured data (company name, address, phone, website, email)

**The key innovation**: Workers run in parallel. Instead of searching cities one at a time, the system can run 10, 20, or even more searches simultaneously.

---

## Visual Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           YOU START HERE                                 │
│                                                                         │
│   "Find all EMS companies in Texas and California"                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        PHASE 1: PLANNING                                │
│                                                                         │
│   🧠 Manager Agent (Gemini Pro)                                         │
│                                                                         │
│   Reads your request and creates a task list:                           │
│   • Task 1: Search Houston, TX                                          │
│   • Task 2: Search Dallas, TX                                           │
│   • Task 3: Search Austin, TX                                           │
│   • Task 4: Search Los Angeles, CA                                      │
│   • Task 5: Search San Francisco, CA                                    │
│   • ... (continues for all major cities)                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       PHASE 2: EXECUTION                                │
│                                                                         │
│   🐝 Worker Agents (Gemini Flash) - Running in Parallel                 │
│                                                                         │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│   │  Worker 1   │  │  Worker 2   │  │  Worker 3   │  │  Worker 4   │   │
│   │  Houston    │  │  Dallas     │  │  Austin     │  │  L.A.       │   │
│   │  🔍 ───────▶│  │  🔍 ───────▶│  │  🔍 ───────▶│  │  🔍 ───────▶│   │
│   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│                                                                         │
│   All workers search the web simultaneously!                            │
│   Each finds 5-15 businesses and saves the results.                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      PHASE 3: AGGREGATION                               │
│                                                                         │
│   📊 Data Aggregator                                                    │
│                                                                         │
│   • Collects all worker results                                         │
│   • Removes duplicate companies                                         │
│   • Exports to CSV (for Excel) and JSON (for developers)                │
│                                                                         │
│   Final Output:                                                         │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │ Company Name          │ City      │ Phone        │ Website       │  │
│   ├──────────────────────────────────────────────────────────────────┤  │
│   │ Houston EMS Services  │ Houston   │ 713-555-0100 │ houstonems.com│  │
│   │ Texas Ambulance Corp  │ Dallas    │ 214-555-0200 │ texamb.com    │  │
│   │ LA Medical Transport  │ L.A.      │ 310-555-0300 │ lamt.com      │  │
│   └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Key Concepts Explained

### SOPs (Standard Operating Procedures)

SOPs are instruction files written in Markdown that tell the AI agents exactly what to do. They're like scripts for the AI to follow.

**Example**: The Manager SOP says:
> "When given a list of states, identify major cities in each state and create a search task for each city. Output your results as a JSON array."

This ensures consistent, predictable behavior every time.

**Location**: `sops/manager/` and `sops/worker/`

### Target Configurations

These YAML files define what industry you're researching. Instead of changing code, you just create a new config file.

**Example** (`config/targets/example.yaml`):
```yaml
industry: EMS
search_terms:
  - ambulance company
  - EMS provider
  - emergency medical services
data_fields:
  - company_name
  - address
  - phone
  - website
  - email
```

To research plumbers instead, you'd create a new file with `industry: Plumbing` and different search terms.

### Parallel Execution

Traditional approach (sequential):
```
Search Houston → Wait → Search Dallas → Wait → Search Austin → Wait...
Total time: 10 cities × 30 seconds = 5 minutes
```

Our approach (parallel):
```
Search Houston ─┐
Search Dallas  ─┼─→ All complete together
Search Austin  ─┤
... (7 more)   ─┘
Total time: ~30 seconds (all run at once)
```

The `max_workers` setting controls how many searches run simultaneously.

---

## Project Structure

```
market-research-agent/
│
├── main.py                    # 🚀 Entry point - run this to start
│
├── config/
│   ├── settings.yaml          # ⚙️ Global settings (models, parallelism)
│   └── targets/
│       └── example.yaml       # 🎯 Industry config (EMS example)
│
├── sops/                      # 📋 AI instruction files
│   ├── manager/
│   │   └── research_strategy.md   # Instructions for the Manager
│   └── worker/
│       ├── city_search.md         # Instructions for city searches
│       └── company_research.md    # Instructions for deep research
│
├── src/                       # 💻 Python code
│   ├── orchestrator.py        # Coordinates the whole workflow
│   ├── worker_pool.py         # Manages parallel execution
│   ├── aggregator.py          # Combines and exports results
│   ├── cli_adapters/          # Connects to Gemini CLI
│   └── utils.py               # Helper functions
│
├── data/                      # 📁 Data storage
│   ├── inputs/                # Input files (city lists, etc.)
│   ├── outputs/               # Raw results from each worker
│   └── aggregated/            # Final combined results (CSV/JSON)
│
└── requirements.txt           # 📦 Python dependencies
```

---

## How to Use It

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Verify Gemini CLI is Working
```bash
python main.py check
```
This confirms the Gemini CLI is installed and authenticated.

### Step 3: Run Research
```bash
# Research EMS companies in Texas
python main.py research --target config/targets/example.yaml --states TX

# Research multiple states with more workers
python main.py research --target config/targets/example.yaml --states TX,CA,FL --workers 20
```

### Step 4: Find Your Results
Results are saved in:
- `data/aggregated/results.csv` - Open in Excel
- `data/aggregated/results.json` - For developers/APIs

---

## Creating a New Research Target

Want to research a different industry? Here's how:

### Option 1: Use the Command
```bash
python main.py init-target --industry "Plumbing" --target config/targets/plumbing.yaml
```

### Option 2: Copy and Edit
1. Copy `config/targets/example.yaml`
2. Rename to `config/targets/plumbing.yaml`
3. Edit the content:
```yaml
industry: Plumbing
search_terms:
  - plumber
  - plumbing company
  - plumbing services
  - emergency plumber
data_fields:
  - company_name
  - address
  - phone
  - website
  - email
```

4. Run with your new target:
```bash
python main.py research --target config/targets/plumbing.yaml --states TX
```

---

## Configuration Options

### Settings (`config/settings.yaml`)

| Setting | What It Does | Default |
|---------|--------------|---------|
| `models.manager` | AI model for planning | gemini-3-pro-preview |
| `models.worker` | AI model for searching | gemini-3-flash-preview |
| `parallelism.max_workers` | How many searches run at once | 10 |
| `parallelism.spawn_delay` | Seconds between starting workers | 0.5 |
| `output.formats` | Export formats | json, csv |

### Why Two Different Models?

- **Manager (Pro)**: Smarter but slower and more expensive. Used once per research run to create the plan.
- **Worker (Flash)**: Faster and cheaper. Used many times (once per city). Speed and cost matter more here.

---

## Typical Output

After running research, you'll get a CSV like this:

| company_name | city | state | address | phone | website | email |
|--------------|------|-------|---------|-------|---------|-------|
| ABC Ambulance | Houston | TX | 123 Main St | (713) 555-0100 | abcamb.com | info@abcamb.com |
| Dallas EMS | Dallas | TX | 456 Oak Ave | (214) 555-0200 | dallasems.com | contact@dallasems.com |
| ... | ... | ... | ... | ... | ... | ... |

The system automatically removes duplicates (same company appearing in multiple searches).

---

## Frequently Asked Questions

### How long does a research run take?
Depends on the scope. Researching 3 states with 10 workers typically takes 2-5 minutes.

### How many businesses will it find?
Each city search finds 5-15 businesses. A 3-state search might return 100-300 unique businesses.

### Can it search internationally?
Currently designed for US states only. The SOPs and city mappings are US-focused.

### What if a search fails?
Failed tasks are logged and reported. The system continues with remaining tasks. You can see which cities failed in the final summary.

### Is there a cost?
Yes - each Gemini API call costs money. The Flash model is much cheaper than Pro. Running 50 worker tasks might cost a few cents to a few dollars depending on response length.

---

## Technical Requirements

- **Python 3.10+**
- **Gemini CLI** installed and authenticated
- **Internet connection** (workers search the web)

---

## Summary

The Market Research AI Employee automates the tedious process of finding businesses across multiple cities and states. It uses a smart "Manager" AI to plan the research and fast "Worker" AIs to execute searches in parallel. Results are automatically combined, deduplicated, and exported to formats you can use immediately.

**Key Benefits:**
- ⚡ **Fast**: Parallel execution searches many cities at once
- 📊 **Structured**: Clean CSV/JSON output ready for use
- 🔧 **Flexible**: Easy to target any industry via config files
- 💰 **Cost-effective**: Uses cheaper models for bulk work
