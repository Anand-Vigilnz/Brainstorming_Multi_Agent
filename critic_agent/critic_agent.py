"""Critic Agent using Google Generative AI to evaluate and critique ideas."""
import os
from typing import Dict, Any
import google.generativeai as genai


class CriticAgent:
    """Agent that critiques ideas for feasibility, potential issues, and strengths."""
    
    def __init__(self):
        """Initialize the critic agent with Google Generative AI."""
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
    
    def _critique_idea_impl(self, idea: str) -> Dict[str, Any]:
        """
        Internal implementation of idea critique.
        
        Args:
            idea: The idea to critique
            
        Returns:
            Dictionary containing critique analysis
        """
        prompt = f"""Critique the following idea: {idea}

Provide a comprehensive critique that includes:
1. Strengths: What are the positive aspects of this idea?
2. Potential Issues: What challenges or problems might arise?
3. Feasibility: How feasible is this idea to implement?
4. Recommendations: Any suggestions for improvement?

Format your response as a clear, structured critique."""

        try:
            # Use Google Generative AI to generate critique
            response = self.model.generate_content(prompt)
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            return {
                "critique": response_text,
                "idea": idea
            }
        except Exception as e:
            # Fallback: return error
            return {
                "critique": f"Error generating critique: {str(e)}",
                "idea": idea
            }
    
    async def critique_idea(self, idea: str) -> Dict[str, Any]:
        """
        Critique an idea.
        
        Args:
            idea: The idea to critique
            
        Returns:
            Dictionary containing critique analysis
        """
        return self._critique_idea_impl(idea)

