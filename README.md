# 🧠 MCP-Native Developer Intelligence Suite

> An autonomous multi-agent system built on the **Model Context Protocol (MCP)** to bridge the gap between LLMs and local development environments. Features deep Git history analysis, automated code auditing via AST parsing, and cross-project documentation synthesis using a modular, state-managed **LangGraph** architecture.

---

## 🏗️ Architecture

The system is cleanly separated into two layers:

```
┌─────────────────────────────────────────────────────┐
│                 Intelligence Layer                   │
│          (LangGraph State Machine)                   │
│                                                      │
│   ┌─────────┐   ┌────────────┐   ┌──────────────┐  │
│   │  Scout   │──▶│ Historian  │──▶│ Synthesizer  │  │
│   │ (Files)  │   │   (Git)    │   │  (Report)    │  │
│   └─────────┘   └────────────┘   └──────────────┘  │
└────────────────────────┬────────────────────────────┘
                         │ calls
┌────────────────────────▼────────────────────────────┐
│                  Protocol Layer                      │
│          (MCP Server — stdio transport)              │
│                                                      │
│   ┌──────────────────┐   ┌───────────────────────┐  │
│   │ get_git_history   │   │ analyze_code_structure│  │
│   └──────────────────┘   └───────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Why Two Layers?

- **Protocol Layer** (`mcp_server/`): A standalone MCP server usable with *any* MCP host — Claude Desktop, custom CLIs, or third-party integrations.
- **Intelligence Layer** (`agents/`): A LangGraph state machine that orchestrates multi-step analysis, decoupled from the protocol.

---

## 📂 Project Structure

```
MCP-Native-Developer-Intelligence-Suite/
├── mcp_server/                  # Protocol Layer
│   ├── __init__.py
│   ├── main.py                  # Entry point (stdio runner)
│   └── server.py                # MCP Server + tool registration
├── agents/                      # Intelligence Layer
│   ├── __init__.py
│   ├── state.py                 # TypedDict state definition
│   └── graph.py                 # LangGraph nodes + edges
├── tools/                       # Concrete Developer Tools
│   ├── __init__.py
│   ├── git_analyzer.py          # Git CLI wrapper (subprocess)
│   ├── code_auditor.py          # AST-based static analysis
│   └── doc_generator.py         # Markdown synthesis
├── tests/
│   ├── __init__.py
│   └── test_tools.py            # Unit tests
├── .env.example                 # Environment template
├── .gitignore
├── pyproject.toml               # Dependencies + metadata
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Git installed and in PATH

### Installation

```bash
# Clone the repository
git clone https://github.com/ayushchhipa1509/MCP-Native-Developer-Intelligence-Suite.git
cd MCP-Native-Developer-Intelligence-Suite

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -e ".[dev]"

# Set up environment
copy .env.example .env         # Then fill in your API keys
```

### Run the MCP Server (stdio)

```bash
python -m mcp_server.main
```

### Run the Intelligence Pipeline

```python
from agents.graph import run_intelligence_report

report = run_intelligence_report("C:/path/to/your/project")
print(report)
```

### Run Tests

```bash
pytest tests/ -v
```

---

## 🔧 MCP Tools

### `get_git_history`

Extracts the last N commits with full metadata.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `repo_path` | `string` | *required* | Absolute path to the Git repo |
| `num_commits` | `integer` | `10` | Number of commits (1–500) |

**Returns:** JSON with commits array and contributor statistics.

### `analyze_code_structure`

Performs AST-based static analysis on Python codebases.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `directory_path` | `string` | *required* | Path to analyze |
| `file_extensions` | `string[]` | `[".py"]` | Extensions to include |

**Returns:** JSON with class hierarchies, function signatures, import maps, and metrics.

---

## 🤖 LangGraph Agent Pipeline

The state machine processes projects through three sequential nodes:

| Node | Role | Outputs |
|------|------|---------|
| **Scout** | File discovery + AST analysis | `discovered_files`, `analysis_results` |
| **Historian** | Git history extraction | `git_context` |
| **Synthesizer** | Report generation | `final_report` (Markdown) |

State is managed via a `TypedDict` that accumulates data across nodes:

```python
class AgentState(TypedDict, total=False):
    project_path: str
    discovered_files: list[dict[str, Any]]
    git_context: dict[str, Any]
    analysis_results: dict[str, Any]
    final_report: str
    errors: list[str]
```

---

## 🔌 Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "developer-intel-suite": {
      "command": "python",
      "args": ["-m", "mcp_server.main"],
      "cwd": "C:/path/to/MCP-Native-Developer-Intelligence-Suite"
    }
  }
}
```

---

## 📜 License

MIT

---

*Built with the Model Context Protocol (MCP) and LangGraph.*
