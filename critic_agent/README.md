# Critic Agent

The Critic Agent uses Google ADK to evaluate and critique ideas for feasibility, potential issues, and strengths.

## Responsibilities

- Receives an idea to evaluate
- Analyzes strengths and potential issues
- Assesses feasibility
- Provides recommendations for improvement

## Configuration

Copy `example.env` to `.env` and configure:

```bash
CRITIC_AGENT_PORT=9992
GOOGLE_API_KEY=your_api_key_here
GOOGLE_ADK_MODEL=gemini-1.5-pro
```

## Running

```bash
python -m critic_agent
```

The agent will start on port 9992 (or the configured port) and expose an A2A-compliant endpoint.

## Skills

- `critique_idea`: Provides comprehensive critique of an idea including strengths, issues, and feasibility

