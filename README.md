# Multi-Agent Brainstorming System

A multi-agent system for brainstorming, critiquing, and prioritizing ideas using the A2A (Agent-to-Agent) Protocol and Google ADK.

## Architecture

The system consists of:

- **Host Agent (Orchestrator)**: Coordinates the workflow across all agents
- **Idea Generator Agent**: Generates creative ideas using Google ADK
- **Critic Agent**: Evaluates ideas for feasibility and potential issues
- **Prioritizer Agent**: Ranks ideas based on multiple criteria
- **Streamlit UI**: User interface for interacting with the system

## Architecture Diagram

```
User → Streamlit UI → Host Agent → Remote Agents (via A2A Protocol)
                                    ├── Idea Generator (Google ADK)
                                    ├── Critic (Google ADK)
                                    └── Prioritizer (Google ADK)
```

## Prerequisites

- Python 3.12+
- Google API Key (for Google ADK)
- `uv` (recommended) or `pip`

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd brainstorming-ma
```

2. Install dependencies:
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Configuration

Each agent requires configuration. Copy the `example.env` files to `.env` in each agent directory:

```bash
# Host Agent
cp host_agent/example.env host_agent/.env

# Idea Agent
cp idea_agent/example.env idea_agent/.env
# Edit idea_agent/.env and add your GOOGLE_API_KEY

# Critic Agent
cp critic_agent/example.env critic_agent/.env
# Edit critic_agent/.env and add your GOOGLE_API_KEY

# Prioritizer Agent
cp prioritizer_agent/example.env prioritizer_agent/.env
# Edit prioritizer_agent/.env and add your GOOGLE_API_KEY

# Streamlit App
cp streamlit_app/example.env streamlit_app/.env
```

## Running the System

### Step 1: Start Remote Agents

Open separate terminal windows for each remote agent:

**Terminal 1 - Idea Generator:**
```bash
python -m idea_agent
```

**Terminal 2 - Critic:**
```bash
python -m critic_agent
```

**Terminal 3 - Prioritizer:**
```bash
python -m prioritizer_agent
```

### Step 2: Start Host Agent

**Terminal 4 - Host Agent:**
```bash
python -m host_agent
```

### Step 3: Start Streamlit UI

**Terminal 5 - Streamlit:**
```bash
streamlit run streamlit_app/app.py
```

The Streamlit app will open in your browser at `http://localhost:8502`.

## Usage

1. Open the Streamlit UI in your browser
2. Enter a brainstorming topic (e.g., "Ways to improve remote team collaboration")
3. Click "Generate Ideas"
4. Wait for the agents to process your request
5. Review the prioritized ideas with critiques

## Workflow

1. **User Input**: User enters a topic in the Streamlit UI
2. **Idea Generation**: Host Agent delegates to Idea Generator Agent
3. **Critique**: Host Agent sends each idea to Critic Agent
4. **Prioritization**: Host Agent sends ideas + critiques to Prioritizer Agent
5. **Results**: Prioritized ideas are displayed in the Streamlit UI

## Project Structure

```
brainstorming-ma/
├── host_agent/              # Orchestrator agent
│   ├── __main__.py
│   ├── orchestrator.py
│   ├── remote_agent_connection.py
│   ├── example.env
│   └── README.md
├── idea_agent/              # Idea Generator Agent
│   ├── __main__.py
│   ├── idea_agent.py
│   ├── agent_executor.py
│   ├── example.env
│   └── README.md
├── critic_agent/            # Critic Agent
│   ├── __main__.py
│   ├── critic_agent.py
│   ├── agent_executor.py
│   ├── example.env
│   └── README.md
├── prioritizer_agent/        # Prioritizer Agent
│   ├── __main__.py
│   ├── prioritizer_agent.py
│   ├── agent_executor.py
│   ├── example.env
│   └── README.md
├── streamlit_app/            # Streamlit UI
│   ├── app.py
│   ├── example.env
│   └── README.md
├── pyproject.toml
└── README.md
```

## Technologies

- **A2A Protocol**: Agent-to-Agent communication standard
- **A2A Python SDK**: Python implementation of the A2A protocol
- **Google ADK**: Google Agent Development Kit for AI agents
- **Streamlit**: Web UI framework
- **Python 3.12+**: Programming language

## Agent Ports

- Host Agent: 9999
- Idea Generator: 9991
- Critic: 9992
- Prioritizer: 9993
- Streamlit: 8502 (default)

## Troubleshooting

### Agents not connecting

- Ensure all agents are running
- Check that ports are not in use
- Verify environment variables are set correctly
- Check agent URLs in host agent configuration

### Google ADK errors

- Verify your Google API key is set correctly
- Check that you have access to the specified model
- Ensure your API key has the necessary permissions

### Streamlit connection errors

- Verify the Host Agent is running on the configured port
- Check the HOST_AGENT_URL in streamlit_app/.env

## Contributing

Contributions are welcome! Please follow the existing code structure and add appropriate tests.

## License

[Add your license here]

## References

- [A2A Protocol Documentation](https://a2a-protocol.org/)
- [A2A Python SDK](https://github.com/a2aproject/a2a-python)
- [Google ADK](https://pypi.org/project/google-adk/)
- [A2A Samples](https://github.com/a2aproject/a2a-samples)

