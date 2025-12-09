from typing import Dict, Any, List
import os
import asyncio
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

class IdeaAgent:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            print("Warning: GROQ_API_KEY not found")
        # Use llama-3.1-8b-instant for high-quality idea generation
        self.llm = ChatGroq(
            groq_api_key=self.api_key,
            model_name="llama-3.1-8b-instant",
            temperature=0.7
        )

    async def generate_ideas(self, topic: str) -> Dict[str, Any]:
        prompt = f"Generate 5 creative and distinct brainstorming ideas for the topic: '{topic}'. Return ONLY the ideas as a list."
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # LangChain Groq is synchronous, so we run it in executor
                response = await asyncio.to_thread(self.llm.invoke, prompt)
                # Extract text from LangChain message
                text = response.content if hasattr(response, 'content') else str(response)
                # Split by lines and clean
                ideas = [line.strip().lstrip('- ').lstrip('0123456789. ') for line in text.split('\n') if line.strip()]
                
                return {"ideas": ideas}
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
                        return {"error": "API rate limit exceeded. Please wait a moment and try again.", "ideas": []}
                else:
                    return {"error": error_str, "ideas": []}
        
        return {"error": "Failed after retries", "ideas": []}

    async def handle_task(self, task_input: Dict[str, Any]) -> Dict[str, Any]:
        topic = task_input.get("topic")
        if not topic:
             # Check if it's wrapped in 'input'
            topic = task_input.get("input", {}).get("topic")
            
        if not topic:
            return {"error": "No topic provided"}
            
        return await self.generate_ideas(topic)
