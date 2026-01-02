
import uvicorn
from fastapi import FastAPI
from a2a.types import AgentCard
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPIApplication
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.events import InMemoryQueueManager

from idea_agent.idea_agent import IdeaAgent
from utils.simple_executor import SimpleAgentExecutor

# Logic
agent_logic = IdeaAgent()

# Card
card = AgentCard(
    name="IdeaAgent",
    description="Generates brainstorming ideas",
    instructions="Give me a topic and I will generate ideas.",
    url="http://localhost:9991",
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
    return {"status": "healthy", "service": "idea-agent"}

if __name__ == "__main__":
    print("[IDEA AGENT] Starting on port 9991...")
    uvicorn.run(app, host="0.0.0.0", port=9991)
