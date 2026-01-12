"""Orchestrator agent that coordinates the brainstorming workflow."""
import asyncio
import uuid
from typing import Dict, List, Any
from host_agent.remote_agent_connection import RemoteAgentConnection
from utils.logger import AgentLogger


class Orchestrator:
    """Orchestrates the product development workflow across multiple agents."""
    
    def __init__(self):
        self.remote_connection = RemoteAgentConnection()
        self.logger = AgentLogger("host_agent")
        self._agents_connected = False
        self._last_agent_urls = None  # Track last used URLs to avoid unnecessary reconnections
        self._failed_agents = set()  # Track agents that have failed (circuit breaker pattern)
    
    def _is_403_error(self, result: Dict[str, Any]) -> bool:
        """Check if result indicates a 403 Forbidden error."""
        if isinstance(result, dict):
            # Check for explicit status_code
            if result.get("status_code") == 403:
                return True
            # Check for non_retryable flag (set by our error handler)
            if result.get("non_retryable") and "403" in str(result.get("error", "")):
                return True
            # Check error message for 403/Forbidden
            error_msg = str(result.get("error", "")).lower()
            if "403" in error_msg or "forbidden" in error_msg:
                return True
        return False
    
    def _handle_agent_error(self, agent_name: str, result: Dict[str, Any], workflow_id: str) -> Dict[str, Any]:
        """Handle agent errors, especially 403 Forbidden errors."""
        error = result.get("error", "Unknown error")
        
        # Check for 403 Forbidden error
        if self._is_403_error(result):
            self._failed_agents.add(agent_name)
            error_msg = (
                f"{agent_name} agent returned 403 Forbidden. "
                "This indicates an authentication/authorization failure. "
                "Please check: 1) API key is valid (API_KEY), "
                "2) API key matches the workflow configuration, "
                "3) AgentGuard proxy is properly configured."
            )
            self.logger.log_error(f"{agent_name} agent authentication failed", ValueError(error_msg), {
                "workflow_id": workflow_id,
                "agent": agent_name,
                "status_code": 403,
                "non_retryable": True
            })
            return {
                "status": "error",
                "message": error_msg,
                "agent": agent_name,
                "status_code": 403,
                "workflow_id": workflow_id,
                "non_retryable": True
            }
        
        # For other errors, return standard error response
        return {
            "status": "error",
            "message": error,
            "agent": agent_name,
            "workflow_id": workflow_id
        }
    
    async def _ensure_connected(self, agent_urls: Dict[str, str] = None, api_key: str = None):
        """Ensure agents are connected (lazy initialization)."""
        # Convert agent_urls to a comparable format (remove None values for comparison)
        normalized_urls = {k: v for k, v in (agent_urls or {}).items() if v} if agent_urls else None
        
        # Only reconnect if:
        # 1. Not yet connected, OR
        # 2. URLs are provided AND different from what we used before
        should_reconnect = False
        if not self._agents_connected:
            should_reconnect = True
        elif normalized_urls:
            # Compare with stored URLs
            if self._last_agent_urls is None or normalized_urls != self._last_agent_urls:
                should_reconnect = True
        
        if should_reconnect:
            if normalized_urls:
                self.logger.log_activity("Connecting/reconnecting to remote agents with provided URLs")
            else:
                self.logger.log_activity("Connecting to remote agents (lazy initialization)")
            await self.remote_connection.discover_all_agents(agent_urls=agent_urls, api_key=api_key)
            self._agents_connected = True
            # Store the URLs we used (normalized to avoid reconnecting when URLs are the same)
            self._last_agent_urls = normalized_urls
        else:
            # URLs are same as before, reuse existing connections
            self.logger.log_activity("Reusing existing agent connections (URLs unchanged)")
    
    async def process_development_request(self, user_request: str, agent_urls: Dict[str, str] = None, api_key: str = None) -> Dict[str, Any]:
        """
        Process a product development request through the multi-agent workflow.
        
        Workflow:
        1. Create architectural plan using Architect Agent
        2. Build code implementation using Developer Agent
        3. Test the code using Tester Agent
        
        Args:
            user_request: The project request/idea (e.g., "build a simple calculator application")
            agent_urls: Optional dictionary with keys: architect_agent_url, developer_agent_url, tester_agent_url
            api_key: Optional API key from UI request. If not provided, falls back to environment variable.
            
        Returns:
            Dictionary containing architectural plan, code, and test results
        """
        workflow_id = str(uuid.uuid4())
        self.logger.log_activity("Starting product development workflow", {
            "workflow_id": workflow_id,
            "user_request": user_request,
            "agent_urls_provided": agent_urls is not None
        })
        
        # Ensure agents are connected (lazy initialization) with optional URLs and API key
        await self._ensure_connected(agent_urls=agent_urls, api_key=api_key)
        
        try:
            # Step 1: Create architectural plan
            self.logger.log_activity("Step 1: Creating architectural plan", {
                "workflow_id": workflow_id,
                "user_request": user_request
            })
            plan_result = await self.remote_connection.send_task_to_architect_agent(user_request)
            
            # Check for 403 errors first (non-retryable authentication failures)
            if self._is_403_error(plan_result):
                return self._handle_agent_error("Architect", plan_result, workflow_id)
            
            # Handle potential 'output' wrapper or direct response
            if "output" in plan_result:
                output_data = plan_result["output"]
                plan = output_data.get("plan")
                error = output_data.get("error")
            else:
                plan = plan_result.get("plan")
                error = plan_result.get("error")
            
            # Check for errors first
            if error:
                self.logger.log_error("Architecture planning failed", ValueError(error), {
                    "workflow_id": workflow_id,
                    "user_request": user_request,
                    "error": error
                })
                return {
                    "status": "error",
                    "message": error,
                    "workflow_id": workflow_id
                }
            
            if not plan:
                self.logger.log_error("No plan generated", ValueError("No plan generated"), {
                    "workflow_id": workflow_id,
                    "user_request": user_request,
                    "raw_response": str(plan_result)
                })
                return {
                    "status": "error",
                    "message": "No architectural plan generated",
                    "workflow_id": workflow_id
                }
            
            self.logger.log_activity("Architectural plan created", {
                "workflow_id": workflow_id
            })
            
            # Step 2: Build code implementation
            self.logger.log_activity("Step 2: Building code implementation", {
                "workflow_id": workflow_id
            })
            
            # Add a small delay between requests to avoid rate limiting
            await asyncio.sleep(1.5)
            
            code_result = await self.remote_connection.send_task_to_developer_agent(plan)
            
            # Check for 403 errors first (non-retryable authentication failures)
            if self._is_403_error(code_result):
                error_response = self._handle_agent_error("Developer", code_result, workflow_id)
                error_response["plan"] = plan  # Include plan in response for context
                return error_response
            
            # Check for errors in code generation response
            if "output" in code_result:
                output_data = code_result["output"]
                code = output_data.get("code")
                error = output_data.get("error")
            else:
                code = code_result.get("code")
                error = code_result.get("error")
            
            if error:
                self.logger.log_error("Code generation failed", ValueError(error), {
                    "workflow_id": workflow_id,
                    "error": error
                })
                return {
                    "status": "error",
                    "message": f"Code generation failed: {error}",
                    "plan": plan,
                    "workflow_id": workflow_id
                }
            
            if not code:
                self.logger.log_error("No code generated", ValueError("No code generated"), {
                    "workflow_id": workflow_id,
                    "raw_response": str(code_result)
                })
                return {
                    "status": "error",
                    "message": "No code generated",
                    "plan": plan,
                    "workflow_id": workflow_id
                }
            
            self.logger.log_activity("Code implementation created", {
                "workflow_id": workflow_id
            })
            
            # Step 3: Test the code
            self.logger.log_activity("Step 3: Testing code", {
                "workflow_id": workflow_id
            })
            
            # Add a small delay between requests to avoid rate limiting
            await asyncio.sleep(1.5)
            
            test_result = await self.remote_connection.send_task_to_tester_agent(code)
            
            # Check for 403 errors first (non-retryable authentication failures)
            if self._is_403_error(test_result):
                error_response = self._handle_agent_error("Tester", test_result, workflow_id)
                error_response["plan"] = plan  # Include plan and code in response for context
                error_response["code"] = code
                return error_response
            
            # Check for errors in test response
            if "output" in test_result:
                output_data = test_result["output"]
                test_results = output_data.get("test_results")
                error = output_data.get("error")
            else:
                test_results = test_result.get("test_results")
                error = test_result.get("error")
            
            if error:
                self.logger.log_error("Testing failed", ValueError(error), {
                    "workflow_id": workflow_id,
                    "error": error
                })
                return {
                    "status": "error",
                    "message": f"Testing failed: {error}",
                    "plan": plan,
                    "code": code,
                    "workflow_id": workflow_id
                }
            
            if not test_results:
                self.logger.log_error("No test results generated", ValueError("No test results"), {
                    "workflow_id": workflow_id,
                    "raw_response": str(test_result)
                })
                return {
                    "status": "error",
                    "message": "No test results generated",
                    "plan": plan,
                    "code": code,
                    "workflow_id": workflow_id
                }
            
            self.logger.log_activity("Workflow completed successfully", {
                "workflow_id": workflow_id
            })
            
            return {
                "status": "success",
                "user_request": user_request,
                "plan": plan,
                "code": code,
                "test_results": test_results,
                "workflow_id": workflow_id
            }
            
        except Exception as e:
            self.logger.log_error("Workflow failed", e, {
                "workflow_id": workflow_id,
                "user_request": user_request
            })
            return {
                "status": "error",
                "message": str(e),
                "workflow_id": workflow_id
            }
    
    async def handle_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an incoming task from the A2A server.
        
        Args:
            task_input: Task input containing the user request/project idea
            
        Returns:
            Task result with plan, code, and test results
        """
        user_request = task_input.get("user_request") or task_input.get("project_idea") or task_input.get("topic", "")
        # Fallback if wrapped in input
        if not user_request:
             user_request = task_input.get("input", {}).get("user_request") or \
                          task_input.get("input", {}).get("project_idea") or \
                          task_input.get("input", {}).get("topic", "")

        if not user_request:
            return {
                "status": "error",
                "message": "User request or project idea is required"
            }
        
        result = await self.process_development_request(user_request)
        return result

