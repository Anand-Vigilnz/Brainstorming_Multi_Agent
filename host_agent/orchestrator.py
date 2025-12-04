"""Orchestrator agent that coordinates the brainstorming workflow."""
import asyncio
import uuid
from typing import Dict, List, Any
from host_agent.remote_agent_connection import RemoteAgentConnection
from utils.logger import AgentLogger


class Orchestrator:
    """Orchestrates the brainstorming workflow across multiple agents."""
    
    def __init__(self):
        self.remote_connection = RemoteAgentConnection()
        self.logger = AgentLogger("host_agent")
    
    async def initialize(self):
        """Initialize orchestrator by discovering all agent cards."""
        await self.remote_connection.discover_all_agents()
    
    async def process_brainstorming_request(self, topic: str) -> Dict[str, Any]:
        """
        Process a brainstorming request through the multi-agent workflow.
        
        Workflow:
        1. Generate ideas using Idea Agent
        2. Critique each idea using Critic Agent
        3. Prioritize ideas using Prioritizer Agent
        
        Args:
            topic: The brainstorming topic/context
            
        Returns:
            Dictionary containing prioritized ideas with critiques
        """
        workflow_id = str(uuid.uuid4())
        self.logger.log_activity("Starting brainstorming workflow", {
            "workflow_id": workflow_id,
            "topic": topic
        })
        
        try:
            # Step 1: Generate ideas
            self.logger.log_activity("Step 1: Generating ideas", {
                "workflow_id": workflow_id,
                "topic": topic
            })
            ideas_result = await self.remote_connection.send_task_to_idea_agent(topic)
            ideas = ideas_result.get("output", {}).get("ideas", [])
            
            self.logger.log_activity("Ideas generated", {
                "workflow_id": workflow_id,
                "ideas_count": len(ideas)
            })
            
            if not ideas:
                self.logger.log_error("No ideas generated", ValueError("No ideas generated"), {
                    "workflow_id": workflow_id,
                    "topic": topic
                })
                return {
                    "status": "error",
                    "message": "No ideas generated",
                    "ideas": []
                }
            
            # Step 2: Critique each idea
            self.logger.log_activity("Step 2: Critiquing ideas", {
                "workflow_id": workflow_id,
                "ideas_count": len(ideas)
            })
            ideas_with_critiques = []
            for idx, idea in enumerate(ideas, 1):
                self.logger.log_activity(f"Critiquing idea {idx}/{len(ideas)}", {
                    "workflow_id": workflow_id,
                    "idea_index": idx,
                    "idea_preview": idea[:50] + "..." if len(idea) > 50 else idea
                })
                critique_result = await self.remote_connection.send_task_to_critic_agent(idea)
                critique = critique_result.get("output", {}).get("critique", "")
                ideas_with_critiques.append({
                    "idea": idea,
                    "critique": critique
                })
            
            self.logger.log_activity("All ideas critiqued", {
                "workflow_id": workflow_id,
                "critiqued_count": len(ideas_with_critiques)
            })
            
            # Step 3: Prioritize ideas
            self.logger.log_activity("Step 3: Prioritizing ideas", {
                "workflow_id": workflow_id,
                "ideas_count": len(ideas_with_critiques)
            })
            prioritization_result = await self.remote_connection.send_task_to_prioritizer_agent(
                ideas_with_critiques
            )
            prioritized_ideas = prioritization_result.get("output", {}).get("prioritized_ideas", [])
            
            self.logger.log_activity("Workflow completed successfully", {
                "workflow_id": workflow_id,
                "total_ideas": len(ideas),
                "prioritized_count": len(prioritized_ideas)
            })
            
            return {
                "status": "success",
                "topic": topic,
                "total_ideas": len(ideas),
                "prioritized_ideas": prioritized_ideas,
                "workflow_id": workflow_id
            }
            
        except Exception as e:
            self.logger.log_error("Workflow failed", e, {
                "workflow_id": workflow_id,
                "topic": topic
            })
            return {
                "status": "error",
                "message": str(e),
                "ideas": [],
                "workflow_id": workflow_id
            }
    
    async def handle_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an incoming task from the A2A server.
        
        Args:
            task_input: Task input containing the brainstorming topic
            
        Returns:
            Task result with prioritized ideas
        """
        topic = task_input.get("topic", "")
        if not topic:
            return {
                "status": "error",
                "message": "Topic is required"
            }
        
        result = await self.process_brainstorming_request(topic)
        return result

