# Streamlit UI Application

A user-friendly web interface for interacting with the multi-agent brainstorming system.

## Features

- Input form for brainstorming topics
- Real-time progress display
- Results visualization with prioritized ideas
- Expandable cards showing critiques and prioritization notes

## Configuration

Copy `example.env` to `.env` and configure:

```bash
HOST_AGENT_URL=http://localhost:9999
```

## Running

```bash
streamlit run streamlit_app/app.py
```

The application will open in your default web browser, typically at `http://localhost:8501`.

## Usage

1. Enter a brainstorming topic in the text area
2. Click "Generate Ideas"
3. Wait for the agents to process your request
4. Review the prioritized ideas with critiques

