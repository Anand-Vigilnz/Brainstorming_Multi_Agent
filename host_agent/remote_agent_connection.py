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

project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)



class RemoteAgentConnection:
    """
    Manages connections to remote agents (Architect, Developer, Tester).
    """
    def __init__(self):
        self.logger = AgentLogger("host_agent_connection")
        self.architect_client = None
        self.developer_client = None
        self.tester_client = None
        self.architect_card = None
        self.developer_card = None
        self.tester_card = None
        self._httpx_client = None

    async def _get_httpx_client(self):
        if self._httpx_client is None:
            # Add headers to help with proxy compatibility
            headers = {
                "User-Agent": "Product-Development-Host-Agent/1.0",
            }
            # Add Bearer token if API key is available
            api_key = os.getenv("API_KEY")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                self.logger.log_activity(f"API key loaded (length: {len(api_key)})")
            else:
                self.logger.log_error("API_KEY not found in environment variables", ValueError("API_KEY missing"))
            
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

    async def discover_all_agents(self, agent_urls: Dict[str, str] = None):
        """
        Connects to all required remote agents.
        This is a lazy initialization step.
        
        Args:
            agent_urls: Optional dictionary with keys: architect_agent_url, developer_agent_url, tester_agent_url
                       If provided, these URLs will be used instead of environment variables.
        """
        self.logger.log_activity("Attempting to connect to remote agents...")
        
        # Get agent URLs from provided dict or environment variables
        if agent_urls:
            architect_agent_url = agent_urls.get("architect_agent_url") or os.getenv("ARCHITECT_AGENT_URL")
            developer_agent_url = agent_urls.get("developer_agent_url") or os.getenv("DEVELOPER_AGENT_URL")
            tester_agent_url = agent_urls.get("tester_agent_url") or os.getenv("TESTER_AGENT_URL")
            self.logger.log_activity("Using agent URLs from request (with env fallback)")
        else:
            architect_agent_url = os.getenv("ARCHITECT_AGENT_URL")
            developer_agent_url = os.getenv("DEVELOPER_AGENT_URL")
            tester_agent_url = os.getenv("TESTER_AGENT_URL")
            self.logger.log_activity("Using agent URLs from environment variables")
        
        self.logger.log_activity(f"Architect Agent URL: {architect_agent_url}")
        self.logger.log_activity(f"Developer Agent URL: {developer_agent_url}")
        self.logger.log_activity(f"Tester Agent URL: {tester_agent_url}")
        
        # Connect to Architect Agent
        if architect_agent_url:
            try:
                self.architect_client, self.architect_card = await self._connect_to_agent(architect_agent_url)
                self.logger.log_activity(f"Connected to Architect Agent at {architect_agent_url}")
            except Exception as e:
                self.logger.log_error("Failed to connect to Architect Agent", e)
        else:
            self.logger.log_error("Architect Agent URL is not configured", ValueError("Architect Agent URL is missing"))
            
        # Connect to Developer Agent
        if developer_agent_url:
            try:
                self.developer_client, self.developer_card = await self._connect_to_agent(developer_agent_url)
                self.logger.log_activity(f"Connected to Developer Agent at {developer_agent_url}")
            except Exception as e:
                self.logger.log_error("Failed to connect to Developer Agent", e)
        else:
            self.logger.log_error("Developer Agent URL is not configured", ValueError("Developer Agent URL is missing"))
            
        # Connect to Tester Agent
        if tester_agent_url:
            try:
                self.tester_client, self.tester_card = await self._connect_to_agent(tester_agent_url)
                self.logger.log_activity(f"Connected to Tester Agent at {tester_agent_url}")
            except Exception as e:
                self.logger.log_error("Failed to connect to Tester Agent", e)
        else:
            self.logger.log_error("Tester Agent URL is not configured", ValueError("Tester Agent URL is missing"))

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

    async def send_task_to_architect_agent(self, user_request: str) -> Dict[str, Any]:
        if not self.architect_client:
            await self.discover_all_agents()
        if not self.architect_client:
             raise RuntimeError("Architect Agent is not available")
        
        return await self._send_and_collect_response(self.architect_client, {"user_request": user_request})

    async def send_task_to_developer_agent(self, architecture_plan: Dict[str, Any]) -> Dict[str, Any]:
        if not self.developer_client:
            await self.discover_all_agents()
        if not self.developer_client:
             raise RuntimeError("Developer Agent is not available")
        
        return await self._send_and_collect_response(self.developer_client, {"architecture_plan": architecture_plan})

    async def send_task_to_tester_agent(self, code_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.tester_client:
            await self.discover_all_agents()
        if not self.tester_client:
             raise RuntimeError("Tester Agent is not available")
        
        return await self._send_and_collect_response(self.tester_client, {"code": code_data})
