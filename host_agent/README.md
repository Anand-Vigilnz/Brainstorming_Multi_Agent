# Host Agent (Orchestrator)

The Host Agent acts as the orchestrator for the multi-agent brainstorming system. It coordinates the workflow between the Idea Generator, Critic, and Prioritizer agents.

## Responsibilities

- Receives brainstorming requests from the Streamlit UI
- Delegates idea generation to the Idea Generator Agent
- Sends each generated idea to the Critic Agent for evaluation
- Collects critiques and sends them to the Prioritizer Agent
- Returns the final prioritized list of ideas

## Configuration

Copy `example.env` to `.env` and configure:

```bash
HOST_AGENT_PORT=9999
IDEA_AGENT_URL=http://localhost:9991
CRITIC_AGENT_URL=http://localhost:9992
PRIORITIZER_AGENT_URL=http://localhost:9993
```

## Running

```bash
python -m host_agent
```

The agent will start on the configured port and expose an A2A-compliant endpoint.

