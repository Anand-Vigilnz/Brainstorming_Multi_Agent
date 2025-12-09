# Prioritizer Agent

The Prioritizer Agent uses LangChain Groq to rank ideas based on multiple criteria including feasibility, impact, novelty, and cost.

## Responsibilities

- Receives ideas with their critiques
- Evaluates each idea against multiple criteria
- Ranks ideas from highest to lowest priority
- Returns prioritized list with reasoning

## Configuration

Copy `example.env` to `.env` and configure:

```bash
PRIORITIZER_AGENT_PORT=9993
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

## Running

```bash
python -m prioritizer_agent
```

The agent will start on port 9993 (or the configured port) and expose an A2A-compliant endpoint.

## Skills

- `prioritize_ideas`: Ranks ideas based on multiple criteria including feasibility, impact, novelty, and cost

