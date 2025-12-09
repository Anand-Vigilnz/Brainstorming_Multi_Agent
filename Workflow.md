# Multi-Agent Brainstorming System - Project Analysis & Workflow

## 1. Project Overview
This project is a **Multi-Agent System (MAS)** designed to automate the brainstorming process. It employs a **Hub-and-Spoke architecture** where a central **Host Agent (Orchestrator)** coordinates activities among specialized agents: **Idea Agent**, **Critic Agent**, and **Prioritizer Agent**. Users interact with the system via a **Streamlit UI**.

All agents utilize Large Language Models (LLMs) via **Groq (Llama 3.1)** to perform their specific tasks. The communication between agents follows an **Agent-to-Agent (A2A)** protocol over HTTP.

## 2. System Architecture & Network

### Components & Endpoints
The system consists of 5 distinct network entities running locally:

| Component | Role | URL / Port | Description |
|-----------|------|------------|-------------|
| **Streamlit UI** | Frontend | `localhost:8501` (Default) | User interface for inputting topics and viewing results. |
| **Host Agent** | Orchestrator | `http://localhost:8080` | The central controller. Receives user requests and manages the workflow state. |
| **Idea Agent** | Worker | `http://localhost:9991` | specialized in creative generation. |
| **Critic Agent** | Worker | `http://localhost:9992` | Specialized in critical analysis. |
| **Prioritizer Agent** | Worker | `http://localhost:9993` | Specialized in ranking and selection. |

### Network Communication
- **Internal Protocol**: The agents communicate using a custom **A2A (Agent-to-Agent) Protocol**.
- **Transport**: HTTP/REST.
- **Data Format**: JSON payloads wrapped in message structures.
- **Service Discovery**: The Host Agent uses "Lazy Initialization" to discover and connect to worker agents only when a request is processed.

## 3. Workflow Sequence

The entire process is triggered by a user action and flows sequentially through the agents.

### Step 0: Initialization
1. **User** opens Streamlit UI.
2. **User** enters a brainstorming topic (e.g., "Ways to improve remote work").
3. **User** clicks "Generate Ideas".

### Step 1: Request Submission (UI -> Host)
- **Action**: Streamlit sends a POST request to the Host Agent.
- **Endpoint**: `POST http://localhost:8080/api/brainstorm`
- **Payload**: `{"topic": "Ways to improve remote work"}`
- **Response**: `{"task_id": "uuid-..."}`
- **Note**: The UI immediately starts **polling** the Host Agent (`GET /api/brainstorm/{task_id}`) every 1 second to check for completion.
> [!WARNING]
> **Configuration Mismatch**: The Streamlit app is currently configured to send requests to `http://localhost:8080/agent`, but the Host Agent is configured to run on port `9999` (`http://localhost:9999`). This will cause connection errors unless a proxy is running on 8080 or the configuration is updated.

### Step 2: Orchestration Start (Host Agent)
- The Host Agent receives the request and initializes the `Orchestrator`.
- It performs **Lazy Discovery** to ensure connections to `localhost:9991`, `9992`, and `9993` are active.

### Step 3: Idea Generation (Host -> Idea Agent)
- **Call**: Host sends a task to the Idea Agent.
- **Endpoint**: `http://localhost:9991` (A2A Message Endpoint)
- **Input Data**: `{"topic": "Ways to improve remote work"}`
- **Process**: Idea Agent uses LLM to generate ~5 distinct ideas.
- **Output Data**: `{"ideas": ["Idea 1...", "Idea 2...", ...]}`

### Step 4: Critique Loop (Host -> Critic Agent)
- **Logic**: The Host iterates through *each* idea generated in Step 3.
- **Call**: For each idea, Host sends a task to the Critic Agent.
- **Endpoint**: `http://localhost:9992` (A2A Message Endpoint)
- **Input Data**: `{"idea": "Idea text..."}`
- **Process**: Critic Agent evaluates the idea for feasibility and challenges.
- **Output Data**: `{"critique": "Constructive criticism text..."}`
- **Result**: Host compiles a list of `{"idea": "...", "critique": "..."}` objects.

### Step 5: Prioritization (Host -> Prioritizer Agent)
- **Call**: Host sends the combined list of ideas and critiques to the Prioritizer Agent.
- **Endpoint**: `http://localhost:9993` (A2A Message Endpoint)
- **Input Data**: 
  ```json
  {
    "ideas_with_critiques": [
      {"idea": "...", "critique": "..."},
      {"idea": "...", "critique": "..."}
    ]
  }
  ```
- **Process**: Prioritizer Agent ranks the ideas based on impact and feasibility.
- **Output Data**: 
  ```json
  {
    "prioritized_ideas": [
      {"idea": "...", "rationale": "...", "rank": 1},
      ...
    ]
  }
  ```

### Step 6: Completion & Result Fetch (Host -> UI)
- The Host Agent aggregates the final result and marks the `task_id` as `completed`.
- The User Interface (polling loop) receives the `completed` status.
- **Data Returned to UI**:
  ```json
  {
    "status": "success",
    "artifacts": [
      {
        "name": "brainstorming_result",
        "parsed_content": {
          "prioritized_ideas": [...],
          "total_ideas": 5,
          "workflow_id": "..."
        }
      }
    ]
  }
  ```

### Step 7: Display
- Streamlit renders the results, showing the top prioritized ideas with their rationales in formatted cards.

## 4. Detailed Endpoint & Method Map

### Host Agent Internal Methods (`host_agent/orchestrator.py`)
| Method | Description |
|--------|-------------|
| `process_brainstorming_request(topic)` | Main entry point. Coordinates the calls to all 3 agents. |
| `_ensure_connected()` | Connects `RemoteAgentConnection` to the 3 sub-agents. |

### Remote Connection Methods (`host_agent/remote_agent_connection.py`)
| Method | Target Agent | Description |
|--------|--------------|-------------|
| `send_task_to_idea_agent(topic)` | Idea Agent | Wraps topic in A2A message format and sends. |
| `send_task_to_critic_agent(idea)` | Critic Agent | Wraps single idea in A2A message format. |
| `send_task_to_prioritizer_agent(list)`| Prioritizer Agent | Sends list of dicts for ranking. |

### Agent Logic
1. **Idea Agent** (`idea_agent.py`):
   - `generate_ideas(topic)`: Prompt: "Generate 5 creative... ideas for topic..."
2. **Critic Agent** (`critic_agent.py`):
   - `critique_idea(idea)`: Prompt: "Critique the following idea constructively..."
3. **Prioritizer Agent** (`prioritizer_agent.py`):
   - `prioritize_ideas(list)`: Prompt: "Review... Rank these ideas... Return JSON..."
