import os
import uvicorn
from fastapi import FastAPI
from a2a.types import AgentCard
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPIApplication
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.events import InMemoryQueueManager
from dotenv import load_dotenv
from pathlib import Path
from architect_agent.architect_agent import ArchitectAgent
from utils.simple_executor import SimpleAgentExecutor

# Logic
agent_logic = ArchitectAgent()

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

# Card
card = AgentCard(
    name="ArchitectAgent",
    description="Creates architectural plans for project requests",
    instructions="I am an Architect. Send me a project request/idea and I will create a detailed architectural plan for it.",
    url=os.getenv("ARCHITECT_AGENT_URL", "https://demoarchagent.vigilnz.com"),
    version="0.0.1",
    capabilities={},
    skills=[],
    defaultInputModes={"text"},
    defaultOutputModes={"text"}
)

# Executor & Handlers
task_store = InMemoryTaskStore()
queue_manager = InMemoryQueueManager()

executor = SimpleAgentExecutor(agent_logic.handle_task, task_store=task_store)

request_handler = DefaultRequestHandler(
    agent_executor=executor,
    task_store=task_store,
    queue_manager=queue_manager
)

# App - pass RequestHandler directly
a2a_app = A2AFastAPIApplication(card, request_handler)
app = FastAPI()
a2a_app.add_routes_to_app(app)

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "architect-agent"}

if __name__ == "__main__":
    print("[ARCHITECT AGENT] Starting on port 9991...")
    uvicorn.run(app, host="0.0.0.0", port=9991)

