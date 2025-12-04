"""A2A server wrapper for the Prioritizer Agent."""
from typing import Dict, Any
from prioritizer_agent.prioritizer_agent import PrioritizerAgent


class TaskResult:
    """Simple task result class."""
    def __init__(self, status: str, output: Dict[str, Any]):
        self.status = status
        self.output = output


class PrioritizerAgentExecutor:
    """Wraps the Google ADK agent with A2A server capabilities."""
    
    def __init__(self, agent: PrioritizerAgent):
        self.agent = agent
    
    async def handle_task(self, task) -> TaskResult:
        """
        Handle incoming A2A task requests.
        
        Args:
            task: A2A task containing ideas with critiques
            
        Returns:
            TaskResult with prioritized ideas
        """
        try:
            # Extract ideas with critiques from task input
            ideas_with_critiques = task.input.get("ideas_with_critiques", [])
            if not ideas_with_critiques:
                return TaskResult(
                    status="error",
                    output={"error": "Ideas with critiques are required"}
                )
            
            # Prioritize ideas using the agent
            result = await self.agent.prioritize_ideas(ideas_with_critiques)
            
            return TaskResult(
                status="completed",
                output=result
            )
        except Exception as e:
            return TaskResult(
                status="error",
                output={"error": str(e)}
            )

