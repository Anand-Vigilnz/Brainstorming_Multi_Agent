import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from pathlib import Path
from a2a.types import AgentCard
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPIApplication
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.events import InMemoryQueueManager
from typing import Dict, Any
import asyncio
from uuid import uuid4

from host_agent.orchestrator import Orchestrator
from host_agent.agent_executor import HostAgentExecutor

# Load .env file - try multiple possible locations
project_root = Path(__file__).parent.parent
env_paths = [
    project_root / ".env",
    Path("../.env"),
    Path(".env"),
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        break
else:
    # Try loading from current directory as fallback
    load_dotenv(override=True)

# Setup Agent Card
card = AgentCard(
    name="ProductOwnerHost",
    description="Orchestrates the product development workflow",
    instructions="I am a Product Owner/Orchestrator. Send me a project request and I will coordinate the development workflow through Architect, Developer, and Tester agents.",
    url=os.getenv("HOST_AGENT_URL", "https://demohostagent.vigilnz.com"),
    # url="http://localhost:9999",
    version="0.0.1",
    capabilities={},
    skills=[],
    defaultInputModes={"text"},
    defaultOutputModes={"text"}
)

# Initialize Logic
orchestrator = Orchestrator()
executor = HostAgentExecutor(orchestrator)

# Setup stores
task_store = InMemoryTaskStore()
queue_manager = InMemoryQueueManager()

# REST API task storage (in-memory dict for UI communication)
rest_task_storage: Dict[str, Dict[str, Any]] = {}

# Setup A2A Handler - pass DefaultRequestHandler directly to A2AFastAPIApplication
# (A2AFastAPIApplication wraps it with JSONRPCHandler internally)
request_handler = DefaultRequestHandler(
    agent_executor=executor,
    task_store=task_store,
    queue_manager=queue_manager
)

# Setup FastAPI App - pass RequestHandler, NOT JSONRPCHandler
a2a_app = A2AFastAPIApplication(card, request_handler)
app = FastAPI()
a2a_app.add_routes_to_app(app)

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "host-agent"}

# REST API endpoints for UI communication
@app.post("/send/task")
async def create_development_task(request: Dict[str, Any]):
    """Create a new development task and return task_id."""
    user_request = request.get("user_request") or request.get("project_idea") or request.get("topic", "").strip()
    if not user_request:
        raise HTTPException(status_code=400, detail="User request or project idea is required")
    
    # Extract optional agent URLs and API key from request
    agent_urls = {
        "architect_agent_url": request.get("architect_agent_url"),
        "developer_agent_url": request.get("developer_agent_url"),
        "tester_agent_url": request.get("tester_agent_url")
    }
    api_key = request.get("api_key")  # Extract API key from request
    
    task_id = str(uuid4())
    
    # Initialize task in storage
    rest_task_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "user_request": user_request,
        "result": None,
        "error": None
    }
    
    # Start processing asynchronously with agent URLs and API key
    asyncio.create_task(process_development_task(task_id, user_request, agent_urls, api_key))
    
    return JSONResponse({
        "task_id": task_id,
        "status": "pending"
    })


@app.get("/send/task/{task_id}")
async def get_development_task(task_id: str):
    """Get the status and result of a development task."""
    if task_id not in rest_task_storage:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = rest_task_storage[task_id]
    response = {
        "task_id": task_data["task_id"],
        "status": task_data["status"]
    }
    
    if task_data["status"] == "completed":
        response["result"] = task_data["result"]
    elif task_data["status"] == "failed":
        response["error"] = task_data.get("error", "Unknown error")
    
    return JSONResponse(response)


async def process_development_task(task_id: str, user_request: str, agent_urls: Dict[str, str] = None, api_key: str = None):
    """Process the development task using the orchestrator."""
    try:
        # Update status to running
        rest_task_storage[task_id]["status"] = "running"
        
        # Process using orchestrator with optional agent URLs and API key
        result = await orchestrator.process_development_request(user_request, agent_urls=agent_urls, api_key=api_key)
        
        # Store result
        rest_task_storage[task_id]["status"] = "completed"
        rest_task_storage[task_id]["result"] = result
        
    except Exception as e:
        # Store error
        rest_task_storage[task_id]["status"] = "failed"
        rest_task_storage[task_id]["error"] = str(e)

if __name__ == "__main__":
    print("[HOST AGENT] Starting on port 9999...")
    uvicorn.run(app, host="0.0.0.0", port=9999)
