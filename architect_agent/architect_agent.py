from typing import Dict, Any
import os
import json
import asyncio
from pathlib import Path
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import re

project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

class ArchitectAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("Warning: OPENAI_API_KEY not found")
        # Use gpt-4o-mini for architectural planning
        self.llm = ChatOpenAI(
            openai_api_key=self.api_key,
            model="gpt-4o-mini",
            temperature=0.5
        )

    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """Try multiple methods to extract JSON from LLM response."""
        # Method 1: Try direct parsing
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        
        # Method 2: Remove markdown code blocks and try again
        cleaned_text = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            pass
        
        # Method 3: Try to find JSON object in the text
        try:
            # Look for content between first { and last }
            start_idx = cleaned_text.find('{')
            end_idx = cleaned_text.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = cleaned_text[start_idx:end_idx + 1]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Method 4: Try to fix common JSON issues
        try:
            # Remove trailing commas before closing braces/brackets
            fixed_text = re.sub(r',(\s*[}\]])', r'\1', cleaned_text)
            # Try to extract JSON object again
            start_idx = fixed_text.find('{')
            end_idx = fixed_text.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = fixed_text[start_idx:end_idx + 1]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass
        
        # If all methods fail, return None
        return None

    async def create_architecture_plan(self, user_request: str) -> Dict[str, Any]:
        prompt = (
            f"Create a detailed architectural plan for the following project request: '{user_request}'. "
            f"Your response should be a structured JSON object with the following fields:\n"
            f"- 'project_name': A descriptive name for the project\n"
            f"- 'overview': A brief overview of what the project will do\n"
            f"- 'architecture': Detailed architecture description including components, structure, and design patterns\n"
            f"- 'technologies': List of recommended technologies and frameworks\n"
            f"- 'components': List of main components/modules with descriptions\n"
            f"- 'file_structure': Suggested file/folder structure\n"
            f"- 'dependencies': List of dependencies and libraries needed\n"
            f"Return ONLY valid JSON, no markdown code blocks or additional text."
        )
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # LangChain OpenAI is synchronous, so we run it in executor
                response = await asyncio.to_thread(self.llm.invoke, prompt)
                # Extract text from LangChain message
                text = response.content if hasattr(response, 'content') else str(response)
                
                # Try to extract and parse JSON
                plan = self._extract_json_from_text(text)
                
                if plan:
                    return {"plan": plan}
                else:
                    # Fallback: return as structured text plan
                    return {
                        "plan": {
                            "project_name": user_request,
                            "overview": "Architectural plan generated (raw format)",
                            "raw_response": text,
                            "note": "Could not parse as JSON, returning raw response"
                        }
                    }
                
            except Exception as e:
                error_str = str(e)
                # Check if it's a quota/rate limit error
                if "429" in error_str or "rate limit" in error_str.lower() or "quota" in error_str.lower():
                    if attempt < max_retries - 1:
                        # Longer wait times for quota errors: 5s, 10s, 20s
                        wait_time = 5 * (2 ** attempt)  # 5s, 10s, 20s
                        print(f"Rate limit hit, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        return {"error": "API rate limit exceeded. Please wait a moment and try again.", "plan": None}
                else:
                    # For other errors, return error but don't retry (might be a prompt issue)
                    return {"error": f"Error generating plan: {error_str}", "plan": None}
        
        return {"error": "Failed after retries", "plan": None}

    async def handle_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        user_request = task_input.get("user_request") or task_input.get("project_idea") or task_input.get("topic")
        if not user_request:
            # Check if it's wrapped in 'input'
            user_request = task_input.get("input", {}).get("user_request") or \
                          task_input.get("input", {}).get("project_idea") or \
                          task_input.get("input", {}).get("topic")
            
        if not user_request:
            return {"error": "No user request or project idea provided"}
            
        return await self.create_architecture_plan(user_request)

