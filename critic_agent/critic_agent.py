from typing import Dict, Any
import os
import asyncio
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

class CriticAgent:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            print("Warning: GROQ_API_KEY not found")
        # Use llama-3.1-8b-instant for thoughtful critiques
        self.llm = ChatGroq(
            groq_api_key=self.api_key,
            model_name="llama-3.1-8b-instant",
            temperature=0.5
        )

    async def critique_idea(self, idea: str) -> Dict[str, Any]:
        prompt = f"Critique the following idea constructively: '{idea}'. identifying potential challenges and improvements. Keep it concise."
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # LangChain Groq is synchronous, so we run it in executor
                response = await asyncio.to_thread(self.llm.invoke, prompt)
                # Extract text from LangChain message
                text = response.content if hasattr(response, 'content') else str(response)
                return {"critique": text}
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "rate limit" in error_str.lower() or "quota" in error_str.lower():
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"Rate limit hit, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        return {"error": "API rate limit exceeded. Please wait a moment and try again.", "critique": "Failed to generate critique."}
                else:
                    return {"error": error_str, "critique": "Failed to generate critique."}
        
        return {"error": "Failed after retries", "critique": "Failed to generate critique."}

    async def handle_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        idea = task_input.get("idea")
        if not idea:
             idea = task_input.get("input", {}).get("idea")
             
        if not idea:
            return {"error": "No idea provided"}
            
        return await self.critique_idea(idea)
