# Multi-Agent Brainstorming System

A sophisticated multi-agent system for automated brainstorming, idea critique, and prioritization using the A2A (Agent-to-Agent) Protocol and LangChain Groq. This system demonstrates distributed AI agent communication where specialized agents collaborate to generate, evaluate, and rank creative ideas.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [Usage Guide](#usage-guide)
- [Workflow Details](#workflow-details)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Technologies Used](#technologies-used)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [References](#references)

## Overview

This project implements a **Hub-and-Spoke architecture** where a central **Host Agent (Orchestrator)** coordinates activities among three specialized worker agents:

- **Idea Generator Agent**: Uses LLMs to generate creative brainstorming ideas
- **Critic Agent**: Evaluates ideas for feasibility, potential challenges, and improvements
- **Prioritizer Agent**: Ranks ideas based on impact and feasibility criteria

Users interact with the system through a **Streamlit web interface**, which sends requests to the Host Agent and displays the prioritized results.

### Key Features

- 🤖 **Multi-Agent Architecture**: Independent agents communicate via A2A protocol
- 🔄 **Asynchronous Processing**: Non-blocking task processing with polling mechanism
- 📊 **Structured Workflow**: Sequential idea generation → critique → prioritization
- 🎨 **Modern UI**: Beautiful Streamlit interface with formatted result cards
- 📝 **Comprehensive Logging**: Detailed activity and communication logs
- 🔧 **Error Handling**: Robust error handling with retry logic for API calls

## Architecture

### System Components

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │ HTTP Request
       ▼
┌─────────────────────────────────┐
│      Streamlit UI               │
│    (Port 8501)                  │
└──────┬──────────────────────────┘
       │ REST API
       │ POST /api/brainstorm
       ▼
┌─────────────────────────────────┐
│      Host Agent                 │
│   (Orchestrator)                │
│    (Port 9999)                  │
└──────┬──────────────────────────┘
       │
       ├─── A2A Protocol ───► ┌─────────────────┐
       │                      │  Idea Agent     │
       │                      │  (Port 9991)    │
       │                      │  LangChain Groq │
       │                      └─────────────────┘
       │
       ├─── A2A Protocol ───► ┌─────────────────┐
       │                      │  Critic Agent   │
       │                      │  (Port 9992)    │
       │                      │  LangChain Groq │
       │                      └─────────────────┘
       │
       └─── A2A Protocol ───► ┌─────────────────┐
                              │ Prioritizer     │
                              │ Agent           │
                              │ (Port 9993)     │
                              │ LangChain Groq  │
                              └─────────────────┘
```

### Communication Protocol

- **Streamlit ↔ Host Agent**: REST API (HTTP/JSON)
- **Host Agent ↔ Worker Agents**: A2A Protocol (JSON-RPC over HTTP)
- **Worker Agents**: Direct LLM calls via LangChain Groq

### Network Ports

| Component | Port | URL |
|-----------|------|-----|
| Streamlit UI | 8501 | http://localhost:8501 |
| Host Agent | 9999 | http://localhost:9999 |
| Idea Agent | 9991 | http://localhost:9991 |
| Critic Agent | 9992 | http://localhost:9992 |
| Prioritizer Agent | 9993 | http://localhost:9993 |

## Prerequisites

### Required Software

1. **Python 3.12 or higher**
   ```bash
   python --version  # Should show 3.12.x or higher
   ```

2. **Package Manager** (choose one):
   - **uv** (recommended for faster dependency resolution)
     ```bash
     # Install uv from https://github.com/astral-sh/uv
     # Or via pip:
     pip install uv
     ```
   - **pip** (standard Python package manager)

3. **Groq API Key**
   - Sign up at [Groq Console](https://console.groq.com/)
   - Generate an API key
   - You'll need this for all worker agents (Idea, Critic, Prioritizer)

### Optional Tools

- **Windows Terminal** (Windows): For running `start_agents.bat` to launch all agents simultaneously
- **Git**: For cloning the repository

## Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd Brainstorming_MA
```

### Step 2: Install Dependencies

Choose one of the following methods:

#### Option A: Using uv (Recommended)

```bash
# Install dependencies
uv sync

# Activate virtual environment (created automatically by uv)
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate
```

#### Option B: Using pip

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install project in editable mode
pip install -e .
```

### Step 3: Verify Installation

```bash
# Check that all required packages are installed
python -c "import fastapi, uvicorn, streamlit, langchain_groq, a2a; print('All packages installed successfully!')"
```

## Configuration

Each component requires its own `.env` file. Follow these steps:

### Step 1: Create Environment Files

Copy the example environment files to create actual configuration files:

```bash
# Host Agent
copy host_agent\example.env host_agent\.env

# Idea Agent
copy idea_agent\example.env idea_agent\.env

# Critic Agent
copy critic_agent\example.env critic_agent\.env

# Prioritizer Agent
copy prioritizer_agent\example.env prioritizer_agent\.env

# Streamlit App
copy streamlit_app\example.env streamlit_app\.env
```

**Linux/Mac users**, replace `copy` with `cp`:
```bash
cp host_agent/example.env host_agent/.env
cp idea_agent/example.env idea_agent/.env
cp critic_agent/example.env critic_agent/.env
cp prioritizer_agent/example.env prioritizer_agent/.env
cp streamlit_app/example.env streamlit_app/.env
```

### Step 2: Configure Each Component

#### Host Agent (`host_agent/.env`)

```env
# Server port
HOST_AGENT_PORT=9999

# Agent name
HOST_AGENT_NAME=Brainstorming Orchestrator

# Remote agent URLs (usually no changes needed)
IDEA_AGENT_URL=http://localhost:9991
CRITIC_AGENT_URL=http://localhost:9992
PRIORITIZER_AGENT_URL=http://localhost:9993
```

#### Idea Agent (`idea_agent/.env`)

```env
# Server port
IDEA_AGENT_PORT=9991

# Agent name
IDEA_AGENT_NAME=Idea Generator Agent

# Groq API Configuration - REQUIRED
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

**⚠️ Important**: Replace `your_groq_api_key_here` with your actual Groq API key.

#### Critic Agent (`critic_agent/.env`)

```env
# Server port
CRITIC_AGENT_PORT=9992

# Agent name
CRITIC_AGENT_NAME=Critic Agent

# Groq API Configuration - REQUIRED
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

**⚠️ Important**: Replace `your_groq_api_key_here` with your actual Groq API key.

#### Prioritizer Agent (`prioritizer_agent/.env`)

```env
# Server port
PRIORITIZER_AGENT_PORT=9993

# Agent name
PRIORITIZER_AGENT_NAME=Prioritizer Agent

# Groq API Configuration - REQUIRED
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

**⚠️ Important**: Replace `your_groq_api_key_here` with your actual Groq API key.

#### Streamlit App (`streamlit_app/.env`)

```env
# Host Agent URL
HOST_AGENT_URL=http://localhost:9999
```

**⚠️ Important Configuration Note**: 

The Streamlit app (`streamlit_app/app.py`) currently has a hardcoded URL that may need to be updated. Check line 22 in `app.py`:

- For local development, ensure it's set to: `http://localhost:9999`
- If using a remote host agent, update accordingly
- The `.env` file setting may be overridden by the hardcoded value

## Running the System

The system requires **5 separate processes** to run simultaneously. You can either run them manually in separate terminals or use the provided batch script (Windows only).

### Method 1: Using Batch Script (Windows Only)

If you're on Windows and have Windows Terminal installed, you can use the provided batch script:

```bash
start_agents.bat
```

This will open Windows Terminal with multiple panes, each running one component:
- Top-left: Host Agent
- Top-right: Idea Agent
- Bottom-left: Critic Agent
- Bottom-right: Prioritizer Agent
- New Tab: Streamlit UI

**Note**: You may need to update the paths in `start_agents.bat` to match your installation directory.

### Method 2: Manual Startup (All Platforms)

Open **5 separate terminal windows/tabs** and run each command:

#### Terminal 1: Idea Generator Agent

```bash
# Navigate to project directory (if not already there)
cd Brainstorming_MA

# Activate virtual environment (if using venv)
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Start Idea Agent
python -m idea_agent
```

Expected output:
```
[IDEA AGENT] Starting on port 9991...
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:9991
```

#### Terminal 2: Critic Agent

```bash
cd Brainstorming_MA
# Activate venv if needed
python -m critic_agent
```

Expected output:
```
[CRITIC AGENT] Starting on port 9992...
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:9992
```

#### Terminal 3: Prioritizer Agent

```bash
cd Brainstorming_MA
# Activate venv if needed
python -m prioritizer_agent
```

Expected output:
```
[PRIORITIZER AGENT] Starting on port 9993...
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:9993
```

#### Terminal 4: Host Agent

```bash
cd Brainstorming_MA
# Activate venv if needed
python -m host_agent
```

Expected output:
```
[HOST AGENT] Starting on port 9999...
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:9999
```

#### Terminal 5: Streamlit UI

```bash
cd Brainstorming_MA
# Activate venv if needed
streamlit run streamlit_app/app.py
```

Expected output:
```
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

### Verification: Check All Services

Once all services are running, verify they're accessible:

```bash
# Check Idea Agent
curl http://localhost:9991/health  # or open in browser

# Check Critic Agent
curl http://localhost:9992/health

# Check Prioritizer Agent
curl http://localhost:9993/health

# Check Host Agent
curl http://localhost:9999/health

# Streamlit should open automatically in your browser
```

## Usage Guide

### Basic Usage

1. **Open the Streamlit UI**
   - Navigate to `http://localhost:8501` in your web browser
   - You should see the "Multi-Agent Brainstorming System" interface

2. **Enter a Brainstorming Topic**
   - In the text area, enter a topic you'd like to brainstorm
   - Example topics:
     - "Ways to improve remote team collaboration"
     - "Innovative features for a mobile app"
     - "Solutions for urban transportation challenges"

3. **Generate Ideas**
   - Click the "🚀 Generate Ideas" button
   - The system will:
     - Show a "Processing your request..." spinner
     - Generate ideas (typically 5)
     - Critique each idea
     - Prioritize the top 3 ideas

4. **Review Results**
   - Results are displayed in colorful, formatted cards
   - Each prioritized idea shows:
     - **Idea**: The core concept
     - **Rationale**: Why it was ranked highly
   - You can download results as JSON

### Example Topics

- Ways to reduce carbon footprint in daily life
- Innovative features for a mobile app
- Strategies to improve employee engagement
- New product ideas for a tech startup
- Solutions for urban transportation challenges
- Marketing strategies for a new product launch
- Ways to improve customer service
- Features for a smart home automation system

### Understanding the Results

The system returns:
- **Total Ideas Generated**: Number of ideas created (typically 5)
- **Prioritized Ideas**: Top-ranked ideas (typically top 3)
- **Workflow ID**: Unique identifier for this brainstorming session
- **Rationale**: Explanation of why each idea was prioritized

## Workflow Details

### Step-by-Step Process

1. **User Input** (Streamlit UI)
   - User enters a topic and clicks "Generate Ideas"
   - Streamlit sends `POST /api/brainstorm` to Host Agent
   - Payload: `{"topic": "user's topic"}`

2. **Task Creation** (Host Agent)
   - Host Agent creates a new task with unique `task_id`
   - Returns `{"task_id": "...", "status": "pending"}` to Streamlit
   - Streamlit starts polling: `GET /api/brainstorm/{task_id}` every 1 second

3. **Orchestration Start** (Host Agent)
   - Host Agent initializes `Orchestrator`
   - Performs **lazy discovery** of worker agents:
     - Connects to Idea Agent (http://localhost:9991)
     - Connects to Critic Agent (http://localhost:9992)
     - Connects to Prioritizer Agent (http://localhost:9993)

4. **Idea Generation** (Idea Agent)
   - Host Agent sends task to Idea Agent via A2A protocol
   - Input: `{"topic": "user's topic"}`
   - Idea Agent uses LangChain Groq (llama-3.1-8b-instant) to generate ~5 ideas
   - Output: `{"ideas": ["Idea 1", "Idea 2", ...]}`

5. **Critique Loop** (Critic Agent)
   - Host Agent iterates through each generated idea
   - For each idea, sends task to Critic Agent
   - Input: `{"idea": "Idea text"}`
   - Critic Agent evaluates feasibility and potential challenges
   - Output: `{"critique": "Constructive criticism text"}`
   - Result: List of `{"idea": "...", "critique": "..."}` objects

6. **Prioritization** (Prioritizer Agent)
   - Host Agent sends combined ideas + critiques to Prioritizer Agent
   - Input: `{"ideas_with_critiques": [{"idea": "...", "critique": "..."}, ...]}`
   - Prioritizer Agent ranks ideas by impact and feasibility
   - Output: `{"prioritized_ideas": [{"idea": "...", "rationale": "...", "rank": 1}, ...]}`

7. **Task Completion** (Host Agent)
   - Host Agent aggregates final result
   - Updates task status to `"completed"`
   - Stores result: `{"status": "success", "topic": "...", "total_ideas": 5, "prioritized_ideas": [...], "workflow_id": "..."}`

8. **Result Display** (Streamlit UI)
   - Polling detects `status: "completed"`
   - Streamlit displays formatted results with:
     - Statistics (total ideas, prioritized count)
     - Prioritized ideas in colorful cards
     - Download button for JSON export

### Error Handling

- **API Rate Limits**: All agents implement retry logic with exponential backoff
- **Connection Errors**: Logged with detailed error messages
- **Task Timeouts**: Streamlit polls for up to 120 seconds before timing out
- **Agent Failures**: Individual agent failures are logged; workflow continues with available agents

## Project Structure

```
Brainstorming_MA/
│
├── host_agent/                      # Orchestrator Agent
│   ├── __init__.py
│   ├── __main__.py                  # Entry point (FastAPI server on port 9999)
│   ├── orchestrator.py              # Main orchestration logic
│   ├── agent_executor.py            # A2A executor wrapper
│   ├── remote_agent_connection.py   # A2A client for worker agents
│   ├── example.env                  # Environment template
│   ├── .env                         # Actual config (create this)
│   └── README.md                    # Agent-specific documentation
│
├── idea_agent/                      # Idea Generator Agent
│   ├── __init__.py
│   ├── __main__.py                  # Entry point (FastAPI server on port 9991)
│   ├── idea_agent.py                # LLM-powered idea generation logic
│   ├── example.env                  # Environment template
│   ├── .env                         # Actual config (create this)
│   └── README.md
│
├── critic_agent/                    # Critic Agent
│   ├── __init__.py
│   ├── __main__.py                  # Entry point (FastAPI server on port 9992)
│   ├── critic_agent.py              # LLM-powered critique logic
│   ├── example.env                  # Environment template
│   ├── .env                         # Actual config (create this)
│   └── README.md
│
├── prioritizer_agent/               # Prioritizer Agent
│   ├── __init__.py
│   ├── __main__.py                  # Entry point (FastAPI server on port 9993)
│   ├── prioritizer_agent.py         # LLM-powered prioritization logic
│   ├── example.env                  # Environment template
│   ├── .env                         # Actual config (create this)
│   └── README.md
│
├── streamlit_app/                   # Streamlit Web UI
│   ├── __init__.py
│   ├── app.py                       # Main Streamlit application
│   ├── example.env                  # Environment template
│   ├── .env                         # Actual config (create this)
│   └── README.md
│
├── utils/                           # Shared utilities
│   ├── __init__.py
│   ├── logger.py                    # Centralized logging system
│   └── simple_executor.py           # A2A executor for worker agents
│
├── logs/                            # Log files (auto-generated)
│   ├── host_agent_activity.log
│   ├── host_agent_communications.jsonl
│   ├── host_agent_connection_activity.log
│   ├── host_agent_connection_errors.log
│   ├── host_agent_errors.log
│   └── README.md
│
├── pyproject.toml                   # Project dependencies and metadata
├── uv.lock                          # Dependency lock file (if using uv)
├── start_agents.bat                 # Windows batch script to start all agents
├── Workflow.md                      # Detailed workflow documentation
└── README.md                        # This file
```

### Key Files Explained

- **`pyproject.toml`**: Defines project metadata, Python version requirement (3.12+), and all dependencies
- **`host_agent/orchestrator.py`**: Core workflow logic coordinating all agents
- **`host_agent/remote_agent_connection.py`**: A2A protocol client implementation
- **`utils/logger.py`**: Comprehensive logging system for debugging and monitoring
- **`utils/simple_executor.py`**: Generic executor for worker agents
- **`start_agents.bat`**: Convenience script for Windows users

## API Endpoints

### Host Agent REST API

#### Create Brainstorming Task

```http
POST /api/brainstorm
Content-Type: application/json

{
  "topic": "Ways to improve remote team collaboration"
}
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

#### Get Task Status

```http
GET /api/brainstorm/{task_id}
```

**Response (Pending/Running):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running"
}
```

**Response (Completed):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "result": {
    "status": "success",
    "topic": "Ways to improve remote team collaboration",
    "total_ideas": 5,
    "prioritized_ideas": [
      {
        "idea": "Implement virtual coffee breaks",
        "rationale": "High feasibility, immediate impact on team bonding"
      },
      ...
    ],
    "workflow_id": "workflow-uuid"
  }
}
```

**Response (Failed):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error": "Error message here"
}
```

### A2A Protocol Endpoints (Internal)

All worker agents expose A2A protocol endpoints for internal communication:

- **Idea Agent**: `http://localhost:9991/agent`
- **Critic Agent**: `http://localhost:9992/agent`
- **Prioritizer Agent**: `http://localhost:9993/agent`

These are accessed via the A2A SDK and not directly by users.

## Technologies Used

### Core Technologies

- **Python 3.12+**: Programming language
- **FastAPI**: Modern web framework for building APIs (used by all agents)
- **Uvicorn**: ASGI server for running FastAPI applications
- **Streamlit**: Web UI framework for user interface

### AI/ML Technologies

- **LangChain Groq**: Integration library for Groq AI models
- **Groq API**: Fast inference API for LLMs
- **Model**: `llama-3.1-8b-instant` (used by all worker agents)

### Agent Communication

- **A2A Protocol**: Agent-to-Agent communication standard
- **A2A Python SDK**: Python implementation (`a2a-sdk[http-server]`)
- **JSON-RPC**: Communication protocol used by A2A
- **HTTP/HTTPS**: Transport layer

### Utilities

- **python-dotenv**: Environment variable management
- **httpx**: Async HTTP client for A2A communication
- **requests**: HTTP library (fallback)
- **uv**: Fast Python package manager (optional)

## Troubleshooting

### Common Issues and Solutions

#### 1. Agents Not Starting

**Symptoms:**
- Port already in use errors
- "Address already in use" messages

**Solutions:**
```bash
# Windows: Find process using port
netstat -ano | findstr :9999

# Linux/Mac: Find process using port
lsof -i :9999

# Kill the process (replace PID with actual process ID)
# Windows:
taskkill /PID <PID> /F
# Linux/Mac:
kill -9 <PID>
```

#### 2. Agents Not Connecting

**Symptoms:**
- "Failed to connect to [Agent]" errors in logs
- Connection timeout errors

**Solutions:**
- Verify all agents are running:
  ```bash
  # Check each port
  curl http://localhost:9991/health
  curl http://localhost:9992/health
  curl http://localhost:9993/health
  curl http://localhost:9999/health
  ```
- Check firewall settings
- Verify URLs in `host_agent/.env` match actual agent ports
- Ensure agents started successfully (check terminal output)

#### 3. Groq API Errors

**Symptoms:**
- "GROQ_API_KEY not found" warnings
- "API rate limit exceeded" errors
- "429 Too Many Requests" errors

**Solutions:**
- Verify API key is set in all three worker agent `.env` files:
  ```bash
  # Check each file
  type idea_agent\.env
  type critic_agent\.env
  type prioritizer_agent\.env
  ```
- Ensure API key is valid: https://console.groq.com/
- Wait a few minutes if rate limited (Groq has rate limits)
- Check Groq API quota/dashboard

#### 4. Streamlit Connection Errors

**Symptoms:**
- "Connection refused" when clicking "Generate Ideas"
- "Failed to connect to host agent"

**Solutions:**
- Verify Host Agent is running on port 9999:
  ```bash
  curl http://localhost:9999/health
  ```
- Check `streamlit_app/app.py` line 22 - ensure URL matches Host Agent
- Update `streamlit_app/.env` with correct `HOST_AGENT_URL`
- Note: The hardcoded URL in `app.py` may override `.env` file

#### 5. Module Import Errors

**Symptoms:**
- "ModuleNotFoundError: No module named 'xyz'"
- Import errors when starting agents

**Solutions:**
- Ensure virtual environment is activated
- Reinstall dependencies:
  ```bash
  pip install -e .
  # or
  uv sync
  ```
- Verify Python version: `python --version` (should be 3.12+)

#### 6. Task Timeout Errors

**Symptoms:**
- "Task timed out - polling exceeded maximum time"
- Ideas generation takes too long

**Solutions:**
- Check Groq API status
- Verify all agents are responding
- Check logs in `logs/` directory for detailed errors
- Increase timeout in `streamlit_app/app.py` if needed (line 46: `max_polls`)

#### 7. Empty or Invalid Results

**Symptoms:**
- No ideas generated
- JSON parsing errors
- "No prioritized ideas found"

**Solutions:**
- Check agent logs for LLM response issues
- Verify Groq API key is working:
  ```python
  python -c "from langchain_groq import ChatGroq; import os; print('OK' if os.getenv('GROQ_API_KEY') else 'Missing key')"
  ```
- Review `logs/host_agent_activity.log` for workflow issues

### Debugging Tips

1. **Check Logs**: All activity is logged in `logs/` directory
   - `host_agent_activity.log`: Orchestrator activity
   - `host_agent_communications.jsonl`: A2A message logs
   - `host_agent_errors.log`: Error details

2. **Enable Verbose Output**: Check terminal output when starting agents

3. **Test Individual Components**:
   ```bash
   # Test Idea Agent directly
   python -c "from idea_agent.idea_agent import IdeaAgent; import asyncio; agent = IdeaAgent(); print(asyncio.run(agent.generate_ideas('test topic')))"
   ```

4. **Verify Environment Variables**:
   ```bash
   # Windows PowerShell
   Get-Content idea_agent\.env
   
   # Linux/Mac
   cat idea_agent/.env
   ```

## Development

### Adding a New Agent

1. Create new agent directory: `new_agent/`
2. Copy structure from `idea_agent/` or `critic_agent/`
3. Implement agent logic in `new_agent/new_agent.py`
4. Add to `host_agent/orchestrator.py` for integration
5. Update `host_agent/remote_agent_connection.py` with connection logic

### Modifying Agent Behavior

- **Idea Generation**: Edit `idea_agent/idea_agent.py` - modify prompt or LLM parameters
- **Critique Style**: Edit `critic_agent/critic_agent.py` - adjust critique prompt
- **Prioritization Criteria**: Edit `prioritizer_agent/prioritizer_agent.py` - change ranking logic
- **Orchestration Flow**: Edit `host_agent/orchestrator.py` - modify workflow steps

### Testing

Run individual components to test:

```bash
# Test Idea Agent
python -m idea_agent

# Test with curl (in another terminal)
curl -X POST http://localhost:9991/agent -H "Content-Type: application/json" -d '{"topic": "test"}'
```

### Code Style

- Follow Python PEP 8 conventions
- Use type hints where possible
- Add docstrings to classes and functions
- Log important operations using `AgentLogger`

### Logging

The system uses a centralized logging utility (`utils/logger.py`):

```python
from utils.logger import AgentLogger

logger = AgentLogger("my_agent")
logger.log_activity("Important event", {"key": "value"})
logger.log_error("Error message", exception_object, {"context": "data"})
```

Logs are stored in `logs/` directory:
- Activity logs: `{agent_name}_activity.log`
- Error logs: `{agent_name}_errors.log`
- Communication logs: `{agent_name}_communications.jsonl`

## References

### Official Documentation

- [A2A Protocol Documentation](https://a2a-protocol.org/)
- [A2A Python SDK](https://github.com/a2aproject/a2a-python)
- [LangChain Groq Integration](https://python.langchain.com/docs/integrations/chat/groq)
- [Groq API Console](https://console.groq.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [A2A Samples Repository](https://github.com/a2aproject/a2a-samples)

### Getting API Keys

- **Groq API Key**: 
  1. Visit https://console.groq.com/
  2. Sign up or log in
  3. Navigate to API Keys section
  4. Create a new API key
  5. Copy and paste into agent `.env` files

### Additional Resources

- Project workflow details: See `Workflow.md`
- Agent-specific documentation: Check individual `README.md` files in each agent directory
- Log analysis: Review `logs/README.md` for log file formats

## License

[Add your license here]

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Submit a pull request

---

**Need Help?** Check the troubleshooting section or review the logs in `logs/` directory for detailed error information.
