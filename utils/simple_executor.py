
from typing import Callable, Any, Dict
from uuid import uuid4
import json
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events import EventQueue
from a2a.types import TaskStatusUpdateEvent, TaskStatus, TaskArtifactUpdateEvent, Artifact, TextPart
from datetime import datetime, timezone as time_timezone

class SimpleAgentExecutor(AgentExecutor):
    def __init__(self, processing_function: Callable[[Dict[str, Any]], Any], task_store=None):
        self.processing_function = processing_function
        self.task_store = task_store

    def _extract_input_from_message(self, message) -> Dict[str, Any]:
        """Extract task input from message, handling various formats."""
        task_input = {}
        
        # Try 1: Check metadata for input
        if hasattr(message, 'metadata') and message.metadata and "input" in message.metadata:
            task_input = message.metadata["input"]
        # Try 2: Check for direct 'input' attribute
        elif hasattr(message, 'input') and message.input:
            task_input = message.input
        # Try 3: Parse JSON from message parts (A2A standard format)
        elif hasattr(message, 'parts') and message.parts:
            for part in message.parts:
                # Part is a RootModel, access part.root to get the actual TextPart/FilePart/DataPart
                actual_part = part.root if hasattr(part, 'root') else part
                
                if hasattr(actual_part, 'kind') and actual_part.kind == 'text' and hasattr(actual_part, 'text'):
                    try:
                        parsed = json.loads(actual_part.text)
                        if isinstance(parsed, dict):
                            task_input = parsed
                            break
                    except json.JSONDecodeError:
                        # Not JSON, maybe raw text - use as topic
                        task_input = {"topic": actual_part.text}
                        break
        
        if not isinstance(task_input, dict):
            if task_input is None:
                task_input = {}
        
        return task_input

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        message = context.message
        
        # Extract input using robust multi-format parser
        task_input = self._extract_input_from_message(message)
        print(f"[SimpleExecutor] Extracted task_input: {task_input}")

        try:
            # Call the Logic
            result = await self.processing_function(task_input)
            print(f"[SimpleExecutor] Result from processing_function: {result}")
            
            # Send the result as an artifact
            result_json = json.dumps(result) if isinstance(result, dict) else str(result)
            
            artifact = Artifact(
                artifact_id=uuid4().hex,
                name="result",
                parts=[TextPart(text=result_json)]
            )
            
            artifact_event = TaskArtifactUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                artifact=artifact,
                last_chunk=True
            )
            await event_queue.enqueue_event(artifact_event)
            
            # Send Completion status
            completion_status = TaskStatus(
                state="completed", 
                timestamp=datetime.now(time_timezone.utc).isoformat()
            )
            
            status_event = TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=completion_status,
                final=True
            )
            await event_queue.enqueue_event(status_event)
            
            # Explicitly update TaskStore if available (for Polling)
            if self.task_store:
                try:
                    task = await self.task_store.get(context.task_id)
                    if task:
                        # Append artifact
                        if not task.artifacts:
                            task.artifacts = []
                        task.artifacts.append(artifact)
                        # Update status
                        task.status = completion_status
                        await self.task_store.save(task)
                        print(f"[SimpleExecutor] Updated TaskStore for task {context.task_id}")
                except Exception as store_e:
                    print(f"[SimpleExecutor] Failed to update TaskStore: {store_e}")
            
        except Exception as e:
            print(f"Error executing task: {e}")
            import traceback
            traceback.print_exc()
            
            # Send error status
            error_status = TaskStatus(
                state="failed",
                timestamp=datetime.now(time_timezone.utc).isoformat(),
                message=None
            )
            event = TaskStatusUpdateEvent(
                 task_id=context.task_id,
                 context_id=context.context_id,
                 status=error_status,
                 final=True
            )
            await event_queue.enqueue_event(event)
            
            # Explicitly update TaskStore on error
            if self.task_store:
                try:
                    task = await self.task_store.get(context.task_id)
                    if task:
                        task.status = error_status
                        await self.task_store.save(task)
                except Exception:
                    pass

    async def cancel(self, task_id: str) -> bool:
        return False

