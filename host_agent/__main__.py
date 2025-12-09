
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
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

# Setup Agent Card
card = AgentCard(
    name="BrainstormingHost",
    description="Orchestrates the brainstorming session",
    instructions="Send me a topic and I will generate, critique, and prioritize ideas.",
    url="http://localhost:9999",
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


# REST API endpoints for UI communication
@app.post("/api/brainstorm")
async def create_brainstorm_task(request: Dict[str, Any]):
    """Create a new brainstorming task and return task_id."""
    topic = request.get("topic", "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required")
    
    task_id = str(uuid4())
    
    # Initialize task in storage
    rest_task_storage[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "topic": topic,
        "result": None,
        "error": None
    }
    
    # Start processing asynchronously
    asyncio.create_task(process_brainstorm_task(task_id, topic))
    
    return JSONResponse({
        "task_id": task_id,
        "status": "pending"
    })


@app.get("/api/brainstorm/{task_id}")
async def get_brainstorm_task(task_id: str):
    """Get the status and result of a brainstorming task."""
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


async def process_brainstorm_task(task_id: str, topic: str):
    """Process the brainstorming task using the orchestrator."""
    try:
        # Update status to running
        rest_task_storage[task_id]["status"] = "running"
        
        # Process using orchestrator
        result = await orchestrator.process_brainstorming_request(topic)
        
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
