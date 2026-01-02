from typing import Any, Dict, List
import asyncio
import json
import os
from uuid import uuid4
import httpx
from pathlib import Path
from dotenv import load_dotenv
# Note: A2AClient is deprecated but still functional.
# When ClientFactory becomes available in the SDK, migrate to: ClientFactory.connect(...)
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams,
    SendMessageRequest,
    GetTaskRequest,
    TaskQueryParams,
)
from utils.logger import AgentLogger

env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# After load_dotenv()
print(f"IDEA_AGENT_URL: {os.getenv('IDEA_AGENT_URL')}")
print(f"CRITIC_AGENT_URL: {os.getenv('CRITIC_AGENT_URL')}")
print(f"PRIORITIZER_AGENT_URL: {os.getenv('PRIORITIZER_AGENT_URL')}")

class RemoteAgentConnection:
    """
    Manages connections to remote agents (Idea, Critic, Prioritizer).
    """
    def __init__(self):
        self.logger = AgentLogger("host_agent_connection")
        self.idea_client = None
        self.critic_client = None
        self.prioritizer_client = None
        self.idea_card = None
        self.critic_card = None
        self.prioritizer_card = None
        self._httpx_client = None

    async def _get_httpx_client(self):
        if self._httpx_client is None:
            # Add headers to help with proxy compatibility
            headers = {
                "User-Agent": "Brainstorming-Host-Agent/1.0",
            }
            self._httpx_client = httpx.AsyncClient(
                timeout=120.0, 
                verify=False,
                headers=headers
            )
        return self._httpx_client

    async def _connect_to_agent(self, base_url: str):
        """Connect to agent and return (client, card) tuple."""
        httpx_client = await self._get_httpx_client()
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)
        card = await resolver.get_agent_card()
        
        # Override the card's URL with the base_url (proxy URL)
        # The agent card may contain an internal URL (e.g., http://localhost:3002/agent/remote1),
        # but we need to use the proxy URL (e.g., https://devagentguard.vigilnz.com/agent/remote1)
        # to connect from the Host Agent
        if hasattr(card, 'url') and card.url != base_url:
            self.logger.log_activity(
                f"Overriding agent card URL from '{card.url}' to '{base_url}' "
                "(using proxy URL instead of internal URL)"
            )
            card.url = base_url
        
        client = A2AClient(httpx_client=httpx_client, agent_card=card)
        return client, card

    async def discover_all_agents(self):
        """
        Connects to all required remote agents.
        This is a lazy initialization step.
        """
        self.logger.log_activity("Attempting to connect to remote agents...")
        
        # Get agent URLs from environment variables with defaults
        idea_agent_url = os.getenv("IDEA_AGENT_URL")
        self.logger.log_activity(f"Idea Agent URL: {idea_agent_url}")
        critic_agent_url = os.getenv("CRITIC_AGENT_URL")
        self.logger.log_activity(f"Critic Agent URL: {critic_agent_url}")
        prioritizer_agent_url = os.getenv("PRIORITIZER_AGENT_URL")
        self.logger.log_activity(f"Prioritizer Agent URL: {prioritizer_agent_url}")
        
        # Connect to Idea Agent
        try:
            self.idea_client, self.idea_card = await self._connect_to_agent(idea_agent_url)
            self.logger.log_activity(f"Connected to Idea Agent at {idea_agent_url}")
        except Exception as e:
            self.logger.log_error("Failed to connect to Idea Agent", e)
            
        # Connect to Critic Agent
        try:
            self.critic_client, self.critic_card = await self._connect_to_agent(critic_agent_url)
            self.logger.log_activity(f"Connected to Critic Agent at {critic_agent_url}")
        except Exception as e:
            self.logger.log_error("Failed to connect to Critic Agent", e)
            
        # Connect to Prioritizer Agent
        try:
            self.prioritizer_client, self.prioritizer_card = await self._connect_to_agent(prioritizer_agent_url)
            self.logger.log_activity(f"Connected to Prioritizer Agent at {prioritizer_agent_url}")
        except Exception as e:
            self.logger.log_error("Failed to connect to Prioritizer Agent", e)

    def _create_message_payload(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create the proper message payload for A2A protocol."""
        return {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': json.dumps(input_data)}
                ],
                'messageId': uuid4().hex,
            },
        }

    async def _send_and_collect_response(self, client: A2AClient, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send a message and collect the final response (Polling)."""
        payload = self._create_message_payload(input_data)
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**payload)
        )
        
        self.logger.log_activity(f"Sending request with payload: {input_data}")
        
        # Retry logic for 403 errors (rate limiting) and other transient errors
        max_retries = 3
        retry_delay = 2  # Start with 2 seconds
        
        for attempt in range(max_retries):
            try:
                # 1. Send Task
                response = await client.send_message(request)
                
                # Access Task from RootModel - handle SendMessageSuccessResponse
                response_data = response.root if hasattr(response, 'root') else response
                
                # Extract task from response
                if hasattr(response_data, 'result'):
                    task = response_data.result
                elif hasattr(response_data, 'id') and hasattr(response_data, 'status'):
                    # It's already a Task object
                    task = response_data
                else:
                    task = response_data
                
                if not task:
                    return {"error": "Empty response from agent"}
                    
                task_id = task.id if hasattr(task, 'id') else None
                if not task_id and hasattr(task, 'root') and hasattr(task.root, 'id'): 
                     task_id = task.root.id

                if not task_id:
                    return {"error": "Could not extract task ID from response"}

                self.logger.log_activity(f"Task submitted with ID: {task_id}. Checking status...")

                # Check if task is already completed
                final_task = None
                if hasattr(task, 'status') and task.status:
                    state = task.status.state if hasattr(task.status, 'state') else None
                    if state == 'completed':
                        final_task = task
                        self.logger.log_activity("Task already completed, using initial response")
                    elif state == 'failed':
                        return {"error": f"Task failed: {getattr(task.status, 'message', 'Unknown error')}"}

                # 2. Poll for completion if not already completed
                if not final_task:
                    import time
                    end_time = time.time() + 60
                    
                    while time.time() < end_time:
                        await asyncio.sleep(1)  # Reduced to 1 second for faster response
                        
                        # Retrieve latest task state
                        try:
                            get_req = GetTaskRequest(
                                id=str(uuid4()),
                                params=TaskQueryParams(id=task_id)
                            )
                            task_response = await client.get_task(get_req)
                        except Exception as e:
                            self.logger.log_error("Error getting task status", e)
                            # Continue polling instead of raising
                            continue
                            
                        # Handle GetTaskSuccessResponse wrapper
                        task_response_data = task_response.root if hasattr(task_response, 'root') else task_response
                        
                        # Extract task from response
                        if hasattr(task_response_data, 'result'):
                            current_task = task_response_data.result
                        elif hasattr(task_response_data, 'id') and hasattr(task_response_data, 'status'):
                            current_task = task_response_data
                        else:
                            current_task = task_response_data
                        
                        if hasattr(current_task, 'status') and current_task.status:
                             state = current_task.status.state if hasattr(current_task.status, 'state') else None
                             if state == 'completed':
                                 final_task = current_task
                                 self.logger.log_activity("Task completed during polling")
                                 break
                             elif state == 'failed':
                                 return {"error": f"Task failed: {getattr(current_task.status, 'message', 'Unknown error')}"}
                    
                    if not final_task:
                        return {"error": "Task timed out waiting for completion"}

                # 3. Parse Artifacts from final task
                final_result = {}
                # Check for errors in final task status again just in case
                if hasattr(final_task, 'status') and hasattr(final_task.status, 'state') and final_task.status.state == 'failed':
                     return {"error": f"Task failed: {getattr(final_task.status, 'message', 'Unknown error')}"}

                self.logger.log_activity(f"Final task has artifacts: {hasattr(final_task, 'artifacts')}")
                if hasattr(final_task, 'artifacts'):
                    self.logger.log_activity(f"Artifacts count: {len(final_task.artifacts) if final_task.artifacts else 0}")

                if hasattr(final_task, 'artifacts') and final_task.artifacts:
                    self.logger.log_activity(f"Found {len(final_task.artifacts)} artifacts in task.")
                    for idx, artifact in enumerate(final_task.artifacts):
                        artifact_name = getattr(artifact, 'name', f'artifact_{idx}')
                        self.logger.log_activity(f"Processing artifact {idx}: {artifact_name}")
                        
                        if hasattr(artifact, 'parts') and artifact.parts:
                            self.logger.log_activity(f"Artifact has {len(artifact.parts)} parts")
                            for part_idx, part in enumerate(artifact.parts):
                                # Handle RootModel wrapper if present
                                actual_part = part.root if hasattr(part, 'root') else part
                                
                                part_kind = getattr(actual_part, 'kind', 'unknown')
                                self.logger.log_activity(f"Part {part_idx} kind: {part_kind}")
                                
                                if hasattr(actual_part, 'kind') and actual_part.kind == 'text' and hasattr(actual_part, 'text'):
                                    text_content = actual_part.text
                                    self.logger.log_activity(f"Part {part_idx} text content (first 300 chars): {text_content[:300]}...")
                                    try:
                                        parsed = json.loads(text_content)
                                        if isinstance(parsed, dict):
                                            # Merge results if multiple artifacts
                                            if final_result:
                                                final_result.update(parsed)
                                            else:
                                                final_result = parsed
                                            self.logger.log_activity(f"Successfully parsed result from artifact {idx}, part {part_idx}")
                                            self.logger.log_activity(f"Parsed keys: {list(parsed.keys())}")
                                        else:
                                            self.logger.log_activity(f"Parsed content is not a dict: {type(parsed)}")
                                    except json.JSONDecodeError as e:
                                        self.logger.log_activity(f"JSON decode error on artifact {idx}, part {part_idx}: {e}")
                                        self.logger.log_activity(f"Raw text: {text_content[:500]}")
                                else:
                                    self.logger.log_activity(f"Part {part_idx} is not text or missing content (kind: {part_kind})")
                        else:
                            self.logger.log_activity(f"Artifact {idx} has no parts")
                else:
                     self.logger.log_activity("No artifacts found in final task.")
                     # Log task structure for debugging
                     self.logger.log_activity(f"Task attributes: {[attr for attr in dir(final_task) if not attr.startswith('_')]}")

                if final_result:
                    self.logger.log_activity(f"Returning final result with keys: {list(final_result.keys())}")
                    return final_result
                    
                self.logger.log_error("No result artifacts collected", ValueError("No artifacts"), {
                    "task_id": task_id,
                    "has_artifacts": hasattr(final_task, 'artifacts'),
                    "artifacts_count": len(final_task.artifacts) if hasattr(final_task, 'artifacts') and final_task.artifacts else 0
                })
                return {"error": "No result artifacts collected"}
                
            except Exception as e:
                error_str = str(e)
                # Check if it's a 403 error (rate limiting) or 503 error (service unavailable)
                is_retryable_error = ("403" in error_str or "503" in error_str) and attempt < max_retries - 1
                
                if is_retryable_error:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 2s, 4s, 8s
                    self.logger.log_activity(
                        f"Received {error_str[:50]}... (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying after {wait_time} seconds..."
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # For other errors or final retry, log and return error
                    self.logger.log_error("Error during request", e)
                    return {"error": str(e)}
        
        # This should not be reached, but just in case
        return {"error": "Failed after all retries"}

    async def send_task_to_idea_agent(self, topic: str) -> Dict[str, Any]:
        if not self.idea_client:
            await self.discover_all_agents()
        if not self.idea_client:
             raise RuntimeError("Idea Agent is not available")
        
        return await self._send_and_collect_response(self.idea_client, {"topic": topic})

    async def send_task_to_critic_agent(self, idea: str) -> Dict[str, Any]:
        if not self.critic_client:
            await self.discover_all_agents()
        if not self.critic_client:
             raise RuntimeError("Critic Agent is not available")
        
        return await self._send_and_collect_response(self.critic_client, {"idea": idea})

    async def send_task_to_prioritizer_agent(self, ideas_with_critiques: List[Dict[str, str]]) -> Dict[str, Any]:
        if not self.prioritizer_client:
            await self.discover_all_agents()
        if not self.prioritizer_client:
             raise RuntimeError("Prioritizer Agent is not available")
        
        return await self._send_and_collect_response(self.prioritizer_client, {"ideas_with_critiques": ideas_with_critiques})
