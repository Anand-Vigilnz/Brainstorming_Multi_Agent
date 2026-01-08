from typing import Dict, Any
import os
import json
import asyncio
from pathlib import Path
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

class TesterAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("Warning: OPENAI_API_KEY not found")
        # Use gpt-4o-mini for testing
        self.llm = ChatOpenAI(
            openai_api_key=self.api_key,
            model="gpt-4o-mini",
            temperature=0.2
        )

    async def test_code(self, code_data: Dict[str, Any]) -> Dict[str, Any]:
        # Convert code to string for the prompt
        code_str = json.dumps(code_data, indent=2) if isinstance(code_data, dict) else str(code_data)
        
        prompt = (
            f"Test the following code implementation and provide comprehensive test results.\n\n"
            f"Code Implementation:\n{code_str}\n\n"
            f"Your response should be a JSON object with the following structure:\n"
            f"{{\n"
            f"  'test_summary': 'Overall summary of testing',\n"
            f"  'test_cases': [\n"
            f"    {{\n"
            f"      'test_name': 'Name of the test case',\n"
            f"      'description': 'What this test verifies',\n"
            f"      'status': 'pass' or 'fail',\n"
            f"      'details': 'Detailed test results and findings'\n"
            f"    }}\n"
            f"  ],\n"
            f"  'overall_status': 'pass' or 'fail',\n"
            f"  'issues_found': ['List of any issues or bugs found'],\n"
            f"  'recommendations': ['List of recommendations for improvement']\n"
            f"}}\n"
            f"Analyze the code for correctness, completeness, potential bugs, edge cases, and best practices. "
            f"Return ONLY valid JSON, no markdown code blocks or additional text."
        )
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # LangChain OpenAI is synchronous, so we run it in executor
                response = await asyncio.to_thread(self.llm.invoke, prompt)
                # Extract text from LangChain message
                text = response.content if hasattr(response, 'content') else str(response)
                
                # Try to parse JSON response
                try:
                    # Remove markdown code blocks if present
                    cleaned_text = text.replace("```json", "").replace("```", "").strip()
                    test_result = json.loads(cleaned_text)
                    return {"test_results": test_result}
                except json.JSONDecodeError:
                    # If JSON parsing fails, try to extract JSON from the response
                    import re
                    json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
                    if json_match:
                        test_result = json.loads(json_match.group())
                        return {"test_results": test_result}
                    else:
                        # Fallback: return as text result
                        return {
                            "test_results": {
                                "test_summary": text,
                                "test_cases": [],
                                "overall_status": "unknown",
                                "issues_found": [],
                                "recommendations": []
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
                        return {"error": "API rate limit exceeded. Please wait a moment and try again.", "test_results": None}
                else:
                    return {"error": error_str, "test_results": None}
        
        return {"error": "Failed after retries", "test_results": None}

    async def handle_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        code_data = task_input.get("code") or task_input.get("code_data")
        if not code_data:
            # Check if it's wrapped in 'input'
            code_data = task_input.get("input", {}).get("code") or \
                       task_input.get("input", {}).get("code_data")
             
        if not code_data:
            return {"error": "No code provided for testing"}
            
        return await self.test_code(code_data)

