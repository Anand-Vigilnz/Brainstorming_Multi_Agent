from typing import Dict, Any
import os
import json
import asyncio
from pathlib import Path
from langchain_groq import ChatGroq
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

class DeveloperAgent:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            print("Warning: GROQ_API_KEY not found")
        # Use llama-3.1-8b-instant for code generation
        self.llm = ChatGroq(
            groq_api_key=self.api_key,
            model_name="llama-3.1-8b-instant",
            temperature=0.3
        )

    async def build_code(self, architecture_plan: Dict[str, Any]) -> Dict[str, Any]:
        # Convert plan to string for the prompt
        plan_str = json.dumps(architecture_plan, indent=2) if isinstance(architecture_plan, dict) else str(architecture_plan)
        
        prompt = (
            f"Based on the following architectural plan, generate the complete code implementation.\n\n"
            f"Architectural Plan:\n{plan_str}\n\n"
            f"Your response should be a JSON object with the following structure:\n"
            f"{{\n"
            f"  'files': [\n"
            f"    {{\n"
            f"      'path': 'relative/file/path.ext',\n"
            f"      'content': 'complete file content here',\n"
            f"      'description': 'brief description of what this file does'\n"
            f"    }}\n"
            f"  ],\n"
            f"  'summary': 'Brief summary of the implementation'\n"
            f"}}\n"
            f"Generate all necessary code files based on the architecture. Include proper structure, imports, and implementation. "
            f"Return ONLY valid JSON, no markdown code blocks or additional text."
        )
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # LangChain Groq is synchronous, so we run it in executor
                response = await asyncio.to_thread(self.llm.invoke, prompt)
                # Extract text from LangChain message
                text = response.content if hasattr(response, 'content') else str(response)
                
                # Try to parse JSON response
                try:
                    # Remove markdown code blocks if present
                    cleaned_text = text.replace("```json", "").replace("```", "").strip()
                    code_result = json.loads(cleaned_text)
                    return {"code": code_result}
                except json.JSONDecodeError:
                    # If JSON parsing fails, try to extract JSON from the response
                    import re
                    json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
                    if json_match:
                        code_result = json.loads(json_match.group())
                        return {"code": code_result}
                    else:
                        # Fallback: return as text with single file
                        return {
                            "code": {
                                "files": [{
                                    "path": "main.py",
                                    "content": text,
                                    "description": "Generated code"
                                }],
                                "summary": "Code generated (could not parse as structured JSON)"
                            }
                        }
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "rate limit" in error_str.lower() or "quota" in error_str.lower():
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"Rate limit hit, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        return {"error": "API rate limit exceeded. Please wait a moment and try again.", "code": None}
                else:
                    return {"error": error_str, "code": None}
        
        return {"error": "Failed after retries", "code": None}

    async def handle_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        architecture_plan = task_input.get("architecture_plan") or task_input.get("plan")
        if not architecture_plan:
            # Check if it's wrapped in 'input'
            architecture_plan = task_input.get("input", {}).get("architecture_plan") or \
                               task_input.get("input", {}).get("plan")
             
        if not architecture_plan:
            return {"error": "No architectural plan provided"}
            
        return await self.build_code(architecture_plan)

