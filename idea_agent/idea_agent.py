"""Idea Generator Agent using Google ADK."""
import os
from typing import List, Dict, Any
import google.generativeai as genai


class IdeaGeneratorAgent:
    """Agent that generates creative ideas based on a topic."""
    
    def __init__(self):
        """Initialize the idea generator agent with Google Generative AI."""
        # Configure Google Generative AI
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        
        # Initialize the model
        model_name = os.getenv("GOOGLE_ADK_MODEL", "gemini-2.0-flash")
        try:
            self.model = genai.GenerativeModel(model_name)
        except Exception:
            # Fallback to default model
            self.model = genai.GenerativeModel("gemini-pro")
    
    def _generate_ideas_impl(self, topic: str) -> Dict[str, Any]:
        """
        Internal implementation of idea generation.
        
        Args:
            topic: The brainstorming topic
            
        Returns:
            Dictionary containing generated ideas
        """
        prompt = f"""Generate 5-10 creative and innovative ideas for the following topic: {topic}

For each idea, provide:
- A clear, concise description
- Why it's innovative or valuable

Return the ideas as a list of strings, each idea being one item in the list."""

        try:
            # Use Google Generative AI to generate ideas
            response = self.model.generate_content(prompt)
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            # Parse response to extract ideas
            ideas = self._parse_ideas_from_response(response_text)
            
            return {
                "ideas": ideas,
                "count": len(ideas)
            }
        except Exception as e:
            # Fallback: return error
            return {
                "ideas": [f"Error generating ideas: {str(e)}"],
                "count": 0
            }
    
    def _parse_ideas_from_response(self, response: str) -> List[str]:
        """
        Parse ideas from the agent's response.
        
        Args:
            response: The agent's text response
            
        Returns:
            List of idea strings
        """
        # Simple parsing: split by numbered items or bullet points
        ideas = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
            # Remove numbering/bullets
            line = line.lstrip('0123456789.-) ').strip()
            if line and len(line) > 10:  # Filter out very short lines
                ideas.append(line)
        
        # If parsing didn't work well, return the whole response as one idea
        if not ideas:
            ideas = [response]
        
        # Limit to 10 ideas
        return ideas[:10]
    
    async def generate_ideas(self, topic: str) -> Dict[str, Any]:
        """
        Generate ideas for a given topic.
        
        Args:
            topic: The brainstorming topic
            
        Returns:
            Dictionary containing generated ideas
        """
        return self._generate_ideas_impl(topic)

