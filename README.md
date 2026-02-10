# CodingAssistant — Autonomous Coding Agent

A lightweight autonomous coding agent powered by LangGraph. It plans multi-step tasks, writes and edits code in a sandboxed workspace, searches the web, and streams its entire thought process to a real-time UI.

> **Think of it as a small-scale Devin/OpenHands**: give it a task like *"create a Flask API with auth"* and watch it plan, code, review, and self-correct — all visible in a live activity panel.

![Architecture](https://img.shields.io/badge/LangGraph-Agent%20Pipeline-blueviolet)
![LLM](https://img.shields.io/badge/LLM-OpenRouter%20%7C%20Ollama-orange)
![Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB)

---

## Features

- **Multi-step task planning** — A planner LLM breaks complex requests into `[RESEARCH]`, `[CODE]`, and `[READ]` steps, then a dispatcher executes them in order
- **Specialized agents** — Dedicated sub-agents for coding (file I/O, terminal), web research (search + fetch), and general reasoning
- **Self-correction pipeline** — Reviewer validates tool calls → Optimizer injects corrective prompts → Fallback retries with detailed error context
- **Tool hallucination auto-fix** — 30+ alias mappings automatically correct common LLM mistakes (`read_file` → `read_file_content`, `run_command` → `run_terminal`)
- **Sandboxed execution** — All generated files are written to an isolated `PlaygroundForCodingAssistant/` directory with path traversal protection
- **Real-time streaming UI** — WebSocket-powered React frontend shows the agent's thought process, tool calls, and results as they happen
- **Dual LLM support** — Seamlessly switch between OpenRouter (cloud) and Ollama (local) via environment variable

---

## Architecture

```
User Request
     │
     ▼
┌─────────────┐     ┌──────────────┐
│ Entry Router │────▶│   Planner    │  Generates step-by-step plan
└─────────────┘     └──────┬───────┘
     │ (simple)            │
     ▼                     ▼
┌─────────────┐     ┌──────────────┐
│  Generator   │◀───│  Dispatcher  │  Routes each step to the right agent
└──────┬──────┘     └──────┬───────┘
       │                   │
       │            ┌──────┼──────────┐
       │            ▼      ▼          ▼
       │     ┌──────────┐ ┌────────┐ ┌──────────────┐
       │     │  Coder   │ │Research│ │   Generator   │
       │     │  Agent   │ │ Agent  │ │  (summarize)  │
       │     └────┬─────┘ └───┬────┘ └──────┬───────┘
       │          │           │              │
       ▼          ▼           ▼              │
┌─────────────┐                              │
│  Reviewer    │◀────────────────────────────┘
│  (validate)  │
└──────┬──────┘
       │ ✅ approved        │ ❌ rejected
       ▼                    ▼
┌─────────────┐     ┌──────────────┐
│  Tool Node   │     │  Optimizer   │  Injects corrective prompt
│  (execute)   │     └──────┬───────┘
└──────┬──────┘            │
       │                    ▼
       │             ┌──────────────┐
       │             │   Fallback   │  Retries with error context
       │             └──────────────┘
       ▼
┌─────────────┐
│ Advance Step │──▶ Back to Dispatcher (next step)
└─────────────┘
```

### Node Descriptions

| Node | File | Role |
|------|------|------|
| **Entry Router** | `graph.py` | Decides if the task needs a plan or can go directly to the generator |
| **Planner** | `planner.py` | LLM generates a tagged step-by-step plan (`[RESEARCH]`, `[CODE]`, `[READ]`) |
| **Dispatcher** | `graph.py` | Reads the current step from the plan and routes to the correct agent |
| **Generator** | `nodes.py` | Main LLM agent — can use any tool or answer the user directly |
| **Coder Agent** | `nodes.py` | Specialized for file operations: read, write, edit, terminal commands |
| **Research Agent** | `nodes.py` | Specialized for web tasks: search + fetch in one shot |
| **Reviewer** | `reviewer.py` | Validates tool calls — checks tool names, auto-corrects hallucinations, guardrails on `write_file` |
| **Optimizer** | `optimizer.py` | Generates corrective prompts when the reviewer rejects an action |
| **Fallback** | `fallback.py` | Handles tool execution errors with detailed retry messages (max 3 retries) |
| **Tool Node** | LangGraph `ToolNode` | Executes the actual tool call (file I/O, web fetch, terminal) |
| **Advance Step** | `graph.py` | Increments the plan step counter and loops back to the dispatcher |

---

## Available Tools

| Tool | Description |
|------|-------------|
| `read_file_content(file_path)` | Read a file from the sandbox |
| `write_file(file_path, content)` | Create or overwrite a file |
| `replace_lines(file_path, start, end, content)` | Edit specific lines in a file |
| `list_project_structure()` | List all files in the sandbox |
| `run_terminal(command)` | Execute a whitelisted shell command |
| `web_search(query)` | Search the internet via DuckDuckGo |
| `fetch_web_page(url)` | Fetch and clean a webpage's text content |
| `smart_web_fetch(query)` | Search + fetch best result in one shot |

All file operations are sandboxed to `PlaygroundForCodingAssistant/` with path traversal protection. Terminal commands are restricted to a whitelist of development tools (python, pip, git, npm, node, ls, cat, grep, etc.).

---

## Project Structure

```
CodingAssistant/
├── app/
│   ├── config.py                  # All configuration (paths, LLM, limits)
│   ├── logger.py                  # Logging setup
│   ├── graph/
│   │   ├── graph.py               # LangGraph workflow definition & routing
│   │   ├── nodes.py               # Agent nodes (generator, coder, research)
│   │   ├── planner.py             # Task planning & complexity detection
│   │   ├── reviewer.py            # Tool call validation & auto-correction
│   │   ├── optimizer.py           # Corrective prompt injection
│   │   └── fallback.py            # Error recovery with retry logic
│   ├── llm/
│   │   ├── llm_client.py          # LLM provider abstraction (OpenRouter/Ollama)
│   │   └── robust_parser.py       # Fault-tolerant JSON/XML response parser
│   ├── state/
│   │   └── dev_state.py           # LangGraph state definition (TypedDict)
│   ├── tools/
│   │   ├── fs.py                  # File system tools (read, write, list)
│   │   ├── web.py                 # Web tools (search, fetch, smart_fetch)
│   │   └── terminal.py            # Terminal execution with command whitelist
│   └── utils/
│       └── smart_context_window.py # Context window management for LLM calls
├── frontend/
│   ├── src/
│   │   └── App.tsx                # React UI (chat + activity panel)
│   ├── package.json
│   └── vite.config.ts
├── server.py                      # FastAPI WebSocket server
├── main.py                        # CLI runner (for testing)
├── PlaygroundForCodingAssistant/  # Sandboxed workspace (generated files go here)
└── .env                           # Environment variables (not committed)
```

---

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- An LLM provider:
  - **OpenRouter** (recommended): Get an API key at [openrouter.ai](https://openrouter.ai)
  - **Ollama** (local): Install from [ollama.ai](https://ollama.ai) and pull a model (`ollama pull llama3.2:3b`)

### 1. Clone & Setup Backend

```bash
git clone https://github.com/YOUR_USERNAME/CodingAssistant.git
cd CodingAssistant

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file at the project root:

```env
# LLM Provider: "openrouter" or "ollama"
LLM_PROVIDER=openrouter

# OpenRouter (if using cloud LLM)
OPEN_API_KEY=sk-or-v1-your-key-here
OPEN_MODEL=google/gemini-2.0-flash-001

# Ollama (if using local LLM)
# LLM_PROVIDER=ollama
# Model will default to llama3.2:3b — change in config.py if needed
```

### 3. Setup Frontend

```bash
cd frontend
npm install
cd ..
```

### 4. Run

**Terminal 1 — Backend:**
```bash
python server.py
```
The WebSocket server starts on `ws://localhost:8000/ws`.

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```
The UI opens at `http://localhost:5173`.

### 5. Use It

Type a task in the chat input:
- `"Create a snake game in Python"` — Plans, writes code, reviews it
- `"Search for FastAPI websocket tutorial"` — Searches the web, fetches the best result
- `"Read main.py and add error handling"` — Reads existing files, edits them
- `"List all files in the project"` — Uses the terminal/file tools

Watch the activity panel on the right to see each node's thought process in real time.

---

## Configuration

All settings are in `app/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `MODEL_NAME` | `llama3.2:3b` | Ollama model name |
| `MODEL_TEMPERATURE` | `0.0` | LLM temperature (0 = deterministic) |
| `MAX_RETRIES` | `3` | Max fallback retries before giving up |
| `MAX_CONTEXT_MESSAGES` | `15` | Messages kept in LLM context window |
| `MAX_PLAN_STEPS` | `5` | Max steps the planner can generate |
| `WEB_SEARCH_MAX_RESULTS` | `5` | DuckDuckGo results per search |
| `WEB_PAGE_MAX_CHARS` | `5000` | Max chars fetched from a webpage |
| `FILE_CONTENT_MAX_CHARS` | `10000` | Max chars when reading a file |

---

## Security (in reality bare minimum, you may have to improve to use it)

- **Sandbox isolation**: All file operations are restricted to `PlaygroundForCodingAssistant/`. Path traversal attempts (e.g., `../../etc/passwd`) are blocked by `get_safe_path()`.
- **Command whitelist**: `run_terminal` only allows a curated list of development commands. Shell operators (`|`, `;`, `&&`, `>`) are blocked.
- **Content guardrails**: The reviewer rejects `write_file` calls with suspiciously short content, JSON-wrapped code, or snippet placeholders.

---

## How the Self-Correction Loop Works

1. **Agent** produces a tool call (e.g., `write_file`)
2. **Reviewer** validates it:
   - Tool name exists? If not, try auto-correction from 30+ aliases
   - For `write_file`: content long enough? Not JSON-wrapped? No `$1` placeholders?
3. If **rejected** → **Optimizer** generates a corrective prompt explaining the issue
4. Agent retries with the corrective prompt injected into its system message
5. If the tool **executes but errors** → **Fallback** captures the real error, injects it as context, and retries
6. After **3 failures**, the step is skipped and the plan continues

---

## 🤝 Contributing

This is an early-stage project. Contributions are welcome! Some areas that need work:

- [ ] Conversation memory across messages (currently stateless per message)
- [ ] Streaming token-by-token responses to the frontend
- [ ] File diff display in the UI when the agent edits code
- [ ] Task cancellation from the frontend
- [ ] Unit tests for graph routing logic

---

## 📜 License

MIT

---

## 🙏 Acknowledgments

Built with [LangGraph](https://github.com/langchain-ai/langgraph), [LangChain](https://github.com/langchain-ai/langchain), [FastAPI](https://fastapi.tiangolo.com/), [React](https://react.dev/), and [Vite](https://vitejs.dev/).