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
        self._agents_connected = False
    
    async def _ensure_connected(self):
        """Ensure agents are connected (lazy initialization)."""
        if not self._agents_connected:
            self.logger.log_activity("Connecting to remote agents (lazy initialization)")
            await self.remote_connection.discover_all_agents()
            self._agents_connected = True
    
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
        
        # Ensure agents are connected (lazy initialization)
        await self._ensure_connected()
        
        try:
            # Step 1: Generate ideas
            self.logger.log_activity("Step 1: Generating ideas", {
                "workflow_id": workflow_id,
                "topic": topic
            })
            ideas_result = await self.remote_connection.send_task_to_idea_agent(topic)
            
            # DEBUG: Log the raw response
            self.logger.log_activity(f"Raw ideas_result: {ideas_result}")
            self.logger.log_activity(f"ideas_result type: {type(ideas_result)}")
            self.logger.log_activity(f"ideas_result keys: {list(ideas_result.keys()) if isinstance(ideas_result, dict) else 'N/A'}")
            
            # Handle potential 'output' wrapper or direct response
            # Some A2A implementations wrap result in 'output', others return direct dict
            if "output" in ideas_result:
                output_data = ideas_result["output"]
                ideas = output_data.get("ideas", [])
                error = output_data.get("error")
            else:
                ideas = ideas_result.get("ideas", [])
                error = ideas_result.get("error")
            
            # Check for errors first
            if error:
                self.logger.log_error("Idea generation failed", ValueError(error), {
                    "workflow_id": workflow_id,
                    "topic": topic,
                    "error": error
                })
                return {
                    "status": "error",
                    "message": error,
                    "ideas": [],
                    "workflow_id": workflow_id
                }
            
            self.logger.log_activity("Ideas generated", {
                "workflow_id": workflow_id,
                "ideas_count": len(ideas)
            })
            
            if not ideas:
                self.logger.log_error("No ideas generated", ValueError("No ideas generated"), {
                    "workflow_id": workflow_id,
                    "topic": topic,
                    "raw_response": str(ideas_result)
                })
                return {
                    "status": "error",
                    "message": "No ideas generated",
                    "ideas": [],
                    "workflow_id": workflow_id
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
                
                # Add a small delay between requests to avoid rate limiting on the proxy
                if idx > 1:
                    await asyncio.sleep(1.5)  # 1.5 second delay between requests
                
                critique_result = await self.remote_connection.send_task_to_critic_agent(idea)
                
                # Check for errors in critique response
                if "output" in critique_result:
                    output_data = critique_result["output"]
                    critique = output_data.get("critique", "")
                    error = output_data.get("error")
                else:
                    critique = critique_result.get("critique", "")
                    error = critique_result.get("error")
                
                if error:
                    self.logger.log_error(f"Critique failed for idea {idx}", ValueError(error), {
                        "workflow_id": workflow_id,
                        "idea_index": idx,
                        "error": error
                    })
                    # Use error as critique or skip this idea
                    critique = f"Error: {error}"

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
            
            # Check for errors in prioritization response
            if "output" in prioritization_result:
                output_data = prioritization_result["output"]
                prioritized_ideas = output_data.get("prioritized_ideas", [])
                error = output_data.get("error")
            else:
                prioritized_ideas = prioritization_result.get("prioritized_ideas", [])
                error = prioritization_result.get("error")
            
            if error:
                self.logger.log_error("Prioritization failed", ValueError(error), {
                    "workflow_id": workflow_id,
                    "error": error
                })
                return {
                    "status": "error",
                    "message": f"Prioritization failed: {error}",
                    "ideas": [],
                    "workflow_id": workflow_id
                }
            
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
        # Fallback if wrapped in input
        if not topic:
             topic = task_input.get("input", {}).get("topic", "")

        if not topic:
            return {
                "status": "error",
                "message": "Topic is required"
            }
        
        result = await self.process_brainstorming_request(topic)
        return result

