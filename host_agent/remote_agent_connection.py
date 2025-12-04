"""A2A client connections to remote agents."""
import os
import uuid
from typing import Optional, Dict, Any
import httpx
from utils.logger import AgentLogger


class RemoteAgentConnection:
    """Manages A2A client connections to remote agents."""
    
    def __init__(self):
        self.idea_agent_url: Optional[str] = None
        self.critic_agent_url: Optional[str] = None
        self.prioritizer_agent_url: Optional[str] = None
        
        # Cached agent cards
        self.idea_agent_card: Optional[Dict[str, Any]] = None
        self.critic_agent_card: Optional[Dict[str, Any]] = None
        self.prioritizer_agent_card: Optional[Dict[str, Any]] = None
        
        self.logger = AgentLogger("host_agent")
        self.initialize_connections()
        
    def initialize_connections(self):
        """Initialize connections to remote agents from environment variables."""
        self.idea_agent_url = os.getenv("IDEA_AGENT_URL", "http://localhost:8001")
        self.critic_agent_url = os.getenv("CRITIC_AGENT_URL", "http://localhost:8002")
        self.prioritizer_agent_url = os.getenv("PRIORITIZER_AGENT_URL", "http://localhost:8003")
        self.logger.log_activity("Initialized remote agent connections", {
            "idea_agent_url": self.idea_agent_url,
            "critic_agent_url": self.critic_agent_url,
            "prioritizer_agent_url": self.prioritizer_agent_url
        })
    
    async def discover_agent_card(self, agent_url: str, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Discover an agent card from the agent's well-known endpoint.
        
        Args:
            agent_url: Base URL of the agent
            agent_name: Name of the agent for logging
            
        Returns:
            Agent card dictionary or None if discovery fails
        """
        discovery_url = f"{agent_url}/.well-known/agent-card.json"
        
        try:
            self.logger.log_activity(f"Discovering agent card for {agent_name}", {
                "agent_url": agent_url,
                "discovery_url": discovery_url
            })
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(discovery_url)
                response.raise_for_status()
                agent_card = response.json()
                
                self.logger.log_activity(f"Successfully discovered agent card for {agent_name}", {
                    "agent_name": agent_card.get("name", agent_name),
                    "skills": [skill.get("id") for skill in agent_card.get("skills", [])]
                })
                
                return agent_card
        except Exception as e:
            self.logger.log_error(f"Failed to discover agent card for {agent_name}", e, {
                "agent_url": agent_url,
                "discovery_url": discovery_url
            })
            # Return None - will fall back to direct URL usage
            return None
    
    async def discover_all_agents(self):
        """Discover agent cards for all remote agents."""
        self.logger.log_activity("Starting agent card discovery for all remote agents")
        
        # Discover idea agent
        self.idea_agent_card = await self.discover_agent_card(self.idea_agent_url, "idea_agent")
        
        # Discover critic agent
        self.critic_agent_card = await self.discover_agent_card(self.critic_agent_url, "critic_agent")
        
        # Discover prioritizer agent
        self.prioritizer_agent_card = await self.discover_agent_card(
            self.prioritizer_agent_url, "prioritizer_agent"
        )
        
        discovered_count = sum([
            1 if self.idea_agent_card else 0,
            1 if self.critic_agent_card else 0,
            1 if self.prioritizer_agent_card else 0
        ])
        
        self.logger.log_activity("Agent card discovery completed", {
            "discovered_count": discovered_count,
            "total_agents": 3
        })
    
    async def send_task_to_idea_agent(self, topic: str) -> dict:
        """Send a task to the idea generator agent via A2A protocol."""
        # Discover agent card if not already discovered
        if not self.idea_agent_card:
            self.idea_agent_card = await self.discover_agent_card(self.idea_agent_url, "idea_agent")
        
        # Use discovered URL or fall back to configured URL
        agent_url = self.idea_agent_card.get("url", self.idea_agent_url) if self.idea_agent_card else self.idea_agent_url
        
        request_id = str(uuid.uuid4())
        request_data = {
            "skill": "generate_ideas",
            "input": {"topic": topic}
        }
        
        self.logger.log_request("idea_agent", "generate_ideas", request_data, request_id)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{agent_url}/task",
                    json=request_data,
                    timeout=60.0
                )
                response.raise_for_status()
                response_data = response.json()
                
                self.logger.log_response(
                    "idea_agent",
                    "generate_ideas",
                    request_id,
                    response_data,
                    "success"
                )
                return response_data
        except Exception as e:
            self.logger.log_response(
                "idea_agent",
                "generate_ideas",
                request_id,
                {},
                "error",
                str(e)
            )
            self.logger.log_error("Failed to send task to idea agent", e, {"topic": topic})
            raise
    
    async def send_task_to_critic_agent(self, idea: str) -> dict:
        """Send a task to the critic agent via A2A protocol."""
        # Discover agent card if not already discovered
        if not self.critic_agent_card:
            self.critic_agent_card = await self.discover_agent_card(self.critic_agent_url, "critic_agent")
        
        # Use discovered URL or fall back to configured URL
        agent_url = self.critic_agent_card.get("url", self.critic_agent_url) if self.critic_agent_card else self.critic_agent_url
        
        request_id = str(uuid.uuid4())
        request_data = {
            "skill": "critique_idea",
            "input": {"idea": idea}
        }
        
        self.logger.log_request("critic_agent", "critique_idea", request_data, request_id)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{agent_url}/task",
                    json=request_data,
                    timeout=60.0
                )
                response.raise_for_status()
                response_data = response.json()
                
                self.logger.log_response(
                    "critic_agent",
                    "critique_idea",
                    request_id,
                    response_data,
                    "success"
                )
                return response_data
        except Exception as e:
            self.logger.log_response(
                "critic_agent",
                "critique_idea",
                request_id,
                {},
                "error",
                str(e)
            )
            self.logger.log_error("Failed to send task to critic agent", e, {"idea": idea[:100]})
            raise
    
    async def send_task_to_prioritizer_agent(self, ideas_with_critiques: list) -> dict:
        """Send a task to the prioritizer agent via A2A protocol."""
        # Discover agent card if not already discovered
        if not self.prioritizer_agent_card:
            self.prioritizer_agent_card = await self.discover_agent_card(
                self.prioritizer_agent_url, "prioritizer_agent"
            )
        
        # Use discovered URL or fall back to configured URL
        agent_url = (
            self.prioritizer_agent_card.get("url", self.prioritizer_agent_url)
            if self.prioritizer_agent_card
            else self.prioritizer_agent_url
        )
        
        request_id = str(uuid.uuid4())
        request_data = {
            "skill": "prioritize_ideas",
            "input": {"ideas_with_critiques": ideas_with_critiques}
        }
        
        self.logger.log_request("prioritizer_agent", "prioritize_ideas", request_data, request_id)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{agent_url}/task",
                    json=request_data,
                    timeout=60.0
                )
                response.raise_for_status()
                response_data = response.json()
                
                self.logger.log_response(
                    "prioritizer_agent",
                    "prioritize_ideas",
                    request_id,
                    response_data,
                    "success"
                )
                return response_data
        except Exception as e:
            self.logger.log_response(
                "prioritizer_agent",
                "prioritize_ideas",
                request_id,
                {},
                "error",
                str(e)
            )
            self.logger.log_error("Failed to send task to prioritizer agent", e, {
                "ideas_count": len(ideas_with_critiques)
            })
            raise

