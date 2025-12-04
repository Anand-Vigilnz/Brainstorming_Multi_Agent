"""Entry point for the Host Agent (Orchestrator)."""
import os
import json
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from uvicorn import run
from host_agent.orchestrator import Orchestrator
from utils.logger import AgentLogger


# Load environment variables
load_dotenv()

app = FastAPI(title="Brainstorming Orchestrator")

# Get configuration from environment
port = int(os.getenv("HOST_AGENT_PORT", "8000"))
agent_name = os.getenv("HOST_AGENT_NAME", "Brainstorming Orchestrator")

# Initialize logger
logger = AgentLogger("host_agent")

# Create agent card
agent_card = {
    "name": agent_name,
    "description": "Orchestrates brainstorming workflow across multiple agents",
    "url": f"http://localhost:{port}",
    "skills": [
        {
            "id": "brainstorm",
            "name": "Brainstorm Ideas",
            "description": "Generates, critiques, and prioritizes ideas for a given topic"
        }
    ]
}

orchestrator = Orchestrator()

logger.log_activity("Host agent started", {"port": port, "agent_name": agent_name})


@app.on_event("startup")
async def startup_event():
    """Initialize orchestrator on startup (discover agent cards)."""
    logger.log_activity("Starting agent card discovery on startup")
    await orchestrator.initialize()


@app.get("/.well-known/agent-card.json")
async def get_agent_card():
    """Return the agent card for A2A protocol discovery."""
    logger.log_activity("Agent card requested")
    return JSONResponse(content=agent_card)


@app.post("/task")
async def handle_task(request: Request):
    """Handle incoming A2A task requests."""
    request_id = str(uuid.uuid4())
    
    try:
        # Parse JSON body
        body = await request.json()
        skill = body.get("skill", "")
        task_input = body.get("input", {})
        
        # Log incoming request
        logger.log_incoming_request(
            "streamlit_ui",
            skill,
            {"skill": skill, "input": task_input},
            request_id
        )
        
        if skill != "brainstorm":
            error_msg = f"Unknown skill: {skill}"
            logger.log_error(error_msg, ValueError(error_msg), {"skill": skill})
            raise HTTPException(status_code=400, detail=error_msg)
        
        result = await orchestrator.handle_task(task_input)
        
        # Return result directly (it already has status field)
        # Log outgoing response
        logger.log_outgoing_response(
            "streamlit_ui",
            skill,
            request_id,
            result,
            result.get("status", "success")
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        error_response = {
            "status": "error",
            "message": str(e)
        }
        logger.log_outgoing_response(
            "streamlit_ui",
            body.get("skill", "unknown") if 'body' in locals() else "unknown",
            request_id,
            error_response,
            "error",
            str(e)
        )
        logger.log_error("Error handling task", e, {"request_id": request_id})
        return error_response


if __name__ == "__main__":
    print(f"Host Agent (Orchestrator) starting on port {port}...")
    print(f"Agent Card available at: http://localhost:{port}/.well-known/agent-card.json")
    run(app, host="0.0.0.0", port=port)

