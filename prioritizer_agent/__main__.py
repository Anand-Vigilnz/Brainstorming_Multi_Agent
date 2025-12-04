"""Entry point for the Prioritizer Agent."""
import os
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from uvicorn import run
from prioritizer_agent.prioritizer_agent import PrioritizerAgent
from prioritizer_agent.agent_executor import PrioritizerAgentExecutor
from utils.logger import AgentLogger


# Load environment variables
load_dotenv()

app = FastAPI(title="Prioritizer Agent")

# Get configuration from environment
port = int(os.getenv("PRIORITIZER_AGENT_PORT", "8003"))
agent_name = os.getenv("PRIORITIZER_AGENT_NAME", "Prioritizer Agent")

# Initialize logger
logger = AgentLogger("prioritizer_agent")

# Initialize the Google ADK agent
prioritizer_agent = PrioritizerAgent()

# Create executor
executor = PrioritizerAgentExecutor(prioritizer_agent)

# Create agent card
agent_card = {
    "name": agent_name,
    "description": "Prioritizes ideas based on criteria such as feasibility, impact, novelty, and cost",
    "url": f"http://localhost:{port}",
    "skills": [
        {
            "id": "prioritize_ideas",
            "name": "Prioritize Ideas",
            "description": "Ranks ideas based on multiple criteria including feasibility, impact, novelty, and cost"
        }
    ]
}

logger.log_activity("Prioritizer agent started", {"port": port, "agent_name": agent_name})


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
        body = await request.json()
        skill = body.get("skill", "")
        task_input = body.get("input", {})
        
        # Log incoming request
        logger.log_incoming_request(
            "host_agent",
            skill,
            {"skill": skill, "input": task_input},
            request_id
        )
        
        if skill != "prioritize_ideas":
            error_msg = f"Unknown skill: {skill}"
            logger.log_error(error_msg, ValueError(error_msg), {"skill": skill})
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Create a simple task-like object
        class Task:
            def __init__(self, input_data):
                self.input = input_data
        
        task = Task(task_input)
        result = await executor.handle_task(task)
        
        response_data = {
            "status": result.status if hasattr(result, 'status') else "completed",
            "output": result.output if hasattr(result, 'output') else result
        }
        
        # Log outgoing response
        logger.log_outgoing_response(
            "host_agent",
            skill,
            request_id,
            response_data,
            response_data.get("status", "success")
        )
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        error_response = {
            "status": "error",
            "output": {"error": str(e)}
        }
        logger.log_outgoing_response(
            "host_agent",
            body.get("skill", "unknown") if 'body' in locals() else "unknown",
            request_id,
            error_response,
            "error",
            str(e)
        )
        logger.log_error("Error handling task", e, {"request_id": request_id})
        return error_response


if __name__ == "__main__":
    print(f"Prioritizer Agent starting on port {port}...")
    print(f"Agent Card available at: http://localhost:{port}/.well-known/agent-card.json")
    run(app, host="0.0.0.0", port=port)
