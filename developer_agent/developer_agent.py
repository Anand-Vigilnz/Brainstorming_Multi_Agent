from typing import Dict, Any
import os
import json
import asyncio
import re
from pathlib import Path
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

class DeveloperAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("Warning: OPENAI_API_KEY not found")
        # Use gpt-4o-mini for code generation
        self.llm = ChatOpenAI(
            openai_api_key=self.api_key,
            model="gpt-4o-mini",
            temperature=0.3
        )

    def _clean_json_string(self, text: str) -> str:
        """Remove control characters and clean JSON string."""
        # Remove markdown code blocks
        cleaned = text.replace("```json", "").replace("```", "").strip()
        
        # Remove control characters (except newlines and tabs within string values)
        # Control characters (0x00-0x1F) except \n (0x0A), \r (0x0D), \t (0x09)
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', cleaned)
        
        return cleaned

    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """Try multiple methods to extract JSON from LLM response."""
        # Method 1: Clean and try direct parsing
        try:
            cleaned_text = self._clean_json_string(text)
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            pass
        
        # Method 2: Try to find JSON object in the text
        try:
            cleaned_text = self._clean_json_string(text)
            # Look for content between first { and last }
            start_idx = cleaned_text.find('{')
            end_idx = cleaned_text.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = cleaned_text[start_idx:end_idx + 1]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Method 3: Try to fix common JSON issues
        try:
            cleaned_text = self._clean_json_string(text)
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
        
        # Method 4: Try with strict=False (Python 3.9+) or manual escaping
        try:
            cleaned_text = self._clean_json_string(text)
            # Try to escape control characters in string values
            start_idx = cleaned_text.find('{')
            end_idx = cleaned_text.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = cleaned_text[start_idx:end_idx + 1]
                # Use json.loads with strict=False if available (Python 3.9+)
                try:
                    return json.loads(json_str, strict=False)
                except TypeError:
                    # strict=False not available, try manual escaping
                    # Escape control characters in string values
                    escaped = re.sub(r'(["\'])((?:(?!\1)[^\\]|\\.)*)(\1)', 
                                   lambda m: m.group(1) + re.sub(r'[\x00-\x1F]', 
                                   lambda c: '\\u{:04x}'.format(ord(c.group())), 
                                   m.group(2)) + m.group(3), json_str)
                    return json.loads(escaped)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        
        # If all methods fail, return None
        return None

    async def build_code(self, architecture_plan: Dict[str, Any]) -> Dict[str, Any]:
        # Convert plan to string for the prompt
        # Handle the case where plan might contain raw_response with markdown
        if isinstance(architecture_plan, dict):
            # If there's a raw_response, use it, otherwise convert to JSON
            if "raw_response" in architecture_plan:
                plan_str = architecture_plan["raw_response"]
            else:
                plan_str = json.dumps(architecture_plan, indent=2)
        else:
            plan_str = str(architecture_plan)
        
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
            f"Return ONLY valid JSON, no markdown code blocks or additional text. "
            f"Ensure all string values in the JSON are properly escaped and do not contain unescaped control characters."
        )
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # LangChain OpenAI is synchronous, so we run it in executor
                response = await asyncio.to_thread(self.llm.invoke, prompt)
                # Extract text from LangChain message
                text = response.content if hasattr(response, 'content') else str(response)
                
                # Try to extract and parse JSON using robust method
                code_result = self._extract_json_from_text(text)
                
                if code_result:
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
                    # Log the actual error for debugging
                    print(f"Error in build_code: {error_str}")
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

