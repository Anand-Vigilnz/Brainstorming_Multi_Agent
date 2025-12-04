"""A2A server wrapper for the Idea Generator Agent."""
from typing import Dict, Any
from idea_agent.idea_agent import IdeaGeneratorAgent


class TaskResult:
    """Simple task result class."""
    def __init__(self, status: str, output: Dict[str, Any]):
        self.status = status
        self.output = output


class IdeaAgentExecutor:
    """Wraps the Google ADK agent with A2A server capabilities."""
    
    def __init__(self, agent: IdeaGeneratorAgent):
        self.agent = agent
    
    async def handle_task(self, task) -> TaskResult:
        """
        Handle incoming A2A task requests.
        
        Args:
            task: A2A task containing the brainstorming topic
            
        Returns:
            TaskResult with generated ideas
        """
        try:
            # Extract topic from task input
            topic = task.input.get("topic", "")
            if not topic:
                return TaskResult(
                    status="error",
                    output={"error": "Topic is required"}
                )
            
            # Generate ideas using the agent
            result = await self.agent.generate_ideas(topic)
            
            return TaskResult(
                status="completed",
                output=result
            )
        except Exception as e:
            return TaskResult(
                status="error",
                output={"error": str(e)}
            )

