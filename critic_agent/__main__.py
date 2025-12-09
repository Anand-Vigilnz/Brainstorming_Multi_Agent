
import uvicorn
from fastapi import FastAPI
from a2a.types import AgentCard
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPIApplication
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.events import InMemoryQueueManager

from critic_agent.critic_agent import CriticAgent
from utils.simple_executor import SimpleAgentExecutor

# Logic
agent_logic = CriticAgent()

# Card
card = AgentCard(
    name="CriticAgent",
    description="Critiques brainstorming ideas",
    instructions="Send me an idea and I will provide a constructive critique.",
    url="http://localhost:9992",
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

if __name__ == "__main__":
    print("[CRITIC AGENT] Starting on port 9992...")
    uvicorn.run(app, host="0.0.0.0", port=9992)
