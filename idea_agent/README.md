# Idea Generator Agent

The Idea Generator Agent uses LangChain Groq to generate creative and innovative ideas based on a given topic.

## Responsibilities

- Receives a brainstorming topic
- Generates 5-10 creative ideas
- Returns the ideas in a structured format

## Configuration

Copy `example.env` to `.env` and configure:

```bash
IDEA_AGENT_PORT=9991
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

## Running

```bash
python -m idea_agent
```

The agent will start on port 9991 (or the configured port) and expose an A2A-compliant endpoint.

## Skills

- `generate_ideas`: Generates a list of creative ideas for a given topic

