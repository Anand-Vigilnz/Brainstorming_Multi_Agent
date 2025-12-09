from typing import Dict, Any, List
import os
import json
import re
import asyncio
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

class PrioritizerAgent:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            print("Warning: GROQ_API_KEY not found")
        # Use llama-3.1-8b-instant for analytical prioritization
        self.llm = ChatGroq(
            groq_api_key=self.api_key,
            model_name="llama-3.1-8b-instant",
            temperature=0.3
        )

    async def prioritize_ideas(self, ideas_with_critiques: List[Dict[str, str]]) -> Dict[str, Any]:
        # Format input for the model
        ideas_str = json.dumps(ideas_with_critiques, indent=2)
        prompt = (
            f"Review the following ideas and their critiques:\n{ideas_str}\n\n"
            "Rank these ideas based on feasibility and impact. Return the top 3 items in a JSON format "
            "with a key 'prioritized_ideas' containing the list of selected ideas. Each item should have 'idea' and 'rationale' fields. "
            "Return ONLY valid JSON, no markdown code blocks."
        )
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # LangChain Groq is synchronous, so we run it in executor
                response = await asyncio.to_thread(self.llm.invoke, prompt)
                # Extract text from LangChain message
                text = response.content if hasattr(response, 'content') else str(response)
                
                # Parse JSON response
                try:
                    # Remove markdown code blocks if present
                    cleaned_text = text.replace("```json", "").replace("```", "").strip()
                    result = json.loads(cleaned_text)
                    return result
                except json.JSONDecodeError:
                    # If JSON parsing fails, try to extract JSON from the response
                    json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                        return result
                    else:
                        raise json.JSONDecodeError("No valid JSON found in response", text, 0)
                    
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "rate limit" in error_str.lower() or "quota" in error_str.lower():
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"Rate limit hit, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        return {"error": "API rate limit exceeded. Please wait a moment and try again.", "prioritized_ideas": []}
                else:
                    return {"error": error_str, "prioritized_ideas": []}
        
        return {"error": "Failed after retries", "prioritized_ideas": []}

    async def handle_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        ideas_input = task_input.get("ideas_with_critiques")
        if not ideas_input:
             ideas_input = task_input.get("input", {}).get("ideas_with_critiques")

        if not ideas_input:
            return {"error": "No ideas provided"}
            
        return await self.prioritize_ideas(ideas_input)
