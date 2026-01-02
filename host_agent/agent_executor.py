from typing import Dict, Any
from uuid import uuid4
import json
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events import EventQueue
from a2a.types import Task, TaskStatusUpdateEvent, TaskStatus, TaskArtifactUpdateEvent, Artifact, TextPart
from host_agent.orchestrator import Orchestrator
from utils.logger import AgentLogger
from datetime import datetime, timezone


class HostAgentExecutor(AgentExecutor):
    """Wraps the Orchestrator with A2A server capabilities."""
    
    def __init__(self, orchestrator: Orchestrator):
        # AgentExecutor doesn't need super().__init__() arguments apparently
        self.orchestrator = orchestrator
        self.logger = AgentLogger("host_agent")
    
    def _extract_input_from_message(self, message) -> Dict[str, Any]:
        """Extract task input from message, handling various formats."""
        task_input = {}
        
        print(f"[HostAgent._extract] Starting extraction...")
        
        # Try 1: Check metadata for input
        if hasattr(message, 'metadata') and message.metadata and "input" in message.metadata:
            task_input = message.metadata["input"]
            print(f"[HostAgent._extract] Found in metadata['input']: {task_input}")
        # Try 2: Check for direct 'input' attribute
        elif hasattr(message, 'input') and message.input:
            task_input = message.input
            print(f"[HostAgent._extract] Found in message.input: {task_input}")
        # Try 3: Parse JSON from message parts (A2A standard format)
        elif hasattr(message, 'parts') and message.parts:
            print(f"[HostAgent._extract] Found {len(message.parts)} parts")
            for i, part in enumerate(message.parts):
                print(f"[HostAgent._extract]   Part {i}: {type(part)}")
                
                # Part is a RootModel, access part.root to get the actual TextPart/FilePart/DataPart
                actual_part = part.root if hasattr(part, 'root') else part
                print(f"[HostAgent._extract]   Actual part {i}: {type(actual_part)}")
                
                if hasattr(actual_part, 'kind'):
                    print(f"[HostAgent._extract]   Part {i} kind: {actual_part.kind}")
                if hasattr(actual_part, 'text'):
                    print(f"[HostAgent._extract]   Part {i} text: {actual_part.text[:200] if hasattr(actual_part.text, '__len__') and len(actual_part.text) > 200 else actual_part.text}")
                    
                if hasattr(actual_part, 'kind') and actual_part.kind == 'text' and hasattr(actual_part, 'text'):
                    try:
                        parsed = json.loads(actual_part.text)
                        if isinstance(parsed, dict):
                            task_input = parsed
                            print(f"[HostAgent._extract] Successfully parsed JSON from part {i}: {task_input}")
                            break
                    except json.JSONDecodeError as e:
                        print(f"[HostAgent._extract] JSON decode error on part {i}: {e}")
                        # Not JSON, maybe raw text - use as topic
                        task_input = {"topic": actual_part.text}
                        print(f"[HostAgent._extract] Using raw text as topic from part {i}")
                        break
        else:
            print(f"[HostAgent._extract] No metadata, input, or parts found")
        
        if not isinstance(task_input, dict):
            if task_input is None:
                task_input = {}
                print(f"[HostAgent._extract] task_input was None, set to empty dict")
        
        print(f"[HostAgent._extract] Final task_input: {task_input}")
        return task_input
    
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute the agent task."""
        message = context.message
        
        print(f"[HostAgent] Message type: {type(message)}")
        print(f"[HostAgent] Message attrs: {[a for a in dir(message) if not a.startswith('_')]}")
        
        try:
            task_input = self._extract_input_from_message(message)
            print(f"[HostAgent] Extracted task_input: {task_input}")
            self.logger.log_activity(f"Extracted task_input: {task_input}")
            
            user_request = task_input.get("user_request") or task_input.get("project_idea") or task_input.get("topic", "") if isinstance(task_input, dict) else ""
            print(f"[HostAgent] Extracted user_request: '{user_request}'")
            self.logger.log_activity(f"Extracted user_request: '{user_request}'")
            
            if not user_request:
                print(f"[HostAgent] ERROR: No user request found!")
                self.logger.log_error("User request is required", ValueError("No user request"))
                return

            # Process development request using orchestrator
            result = await self.orchestrator.process_development_request(user_request)
            
            # Send the result as an artifact
            result_json = json.dumps(result) if isinstance(result, dict) else str(result)
            
            artifact = Artifact(
                artifact_id=uuid4().hex,
                name="development_result",
                parts=[TextPart(text=result_json)]
            )
            
            artifact_event = TaskArtifactUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                artifact=artifact,
                last_chunk=True
            )
            await event_queue.enqueue_event(artifact_event)
            
            # Send completion status
            completion_status = TaskStatus(
                state="completed", 
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            status_event = TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=completion_status,
                final=True
            )
            
            await event_queue.enqueue_event(status_event)
            self.logger.log_activity("Execution completed", result)
            
        except Exception as e:
            self.logger.log_error("Error in execute", e)

    async def cancel(self, task_id: str) -> bool:
        return False

