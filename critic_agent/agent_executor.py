"""A2A server wrapper for the Critic Agent."""
from typing import Dict, Any
from critic_agent.critic_agent import CriticAgent


class TaskResult:
    """Simple task result class."""
    def __init__(self, status: str, output: Dict[str, Any]):
        self.status = status
        self.output = output


class CriticAgentExecutor:
    """Wraps the Google ADK agent with A2A server capabilities."""
    
    def __init__(self, agent: CriticAgent):
        self.agent = agent
    
    async def handle_task(self, task) -> TaskResult:
        """
        Handle incoming A2A task requests.
        
        Args:
            task: A2A task containing the idea to critique
            
        Returns:
            TaskResult with critique
        """
        try:
            # Extract idea from task input
            idea = task.input.get("idea", "")
            if not idea:
                return TaskResult(
                    status="error",
                    output={"error": "Idea is required"}
                )
            
            # Critique the idea using the agent
            result = await self.agent.critique_idea(idea)
            
            return TaskResult(
                status="completed",
                output=result
            )
        except Exception as e:
            return TaskResult(
                status="error",
                output={"error": str(e)}
            )

