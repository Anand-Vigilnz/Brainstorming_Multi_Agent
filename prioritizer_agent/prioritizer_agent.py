"""Prioritizer Agent using Google Generative AI to rank ideas based on criteria."""
import os
from typing import List, Dict, Any
import google.generativeai as genai


class PrioritizerAgent:
    """Agent that prioritizes ideas based on criteria like feasibility, impact, novelty, and cost."""
    
    def __init__(self):
        """Initialize the prioritizer agent with Google Generative AI."""
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
    
    def _prioritize_ideas_impl(self, ideas_with_critiques: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Internal implementation of idea prioritization.
        
        Args:
            ideas_with_critiques: List of dictionaries containing ideas and their critiques
            
        Returns:
            Dictionary containing prioritized ideas
        """
        # Format the input for the prompt
        ideas_text = ""
        for idx, item in enumerate(ideas_with_critiques, 1):
            idea = item.get("idea", "")
            critique = item.get("critique", "")
            ideas_text += f"\n{idx}. Idea: {idea}\n   Critique: {critique}\n"
        
        prompt = f"""Prioritize the following ideas based on these criteria:
1. Feasibility: How easy is it to implement?
2. Impact: What is the potential impact or value?
3. Novelty: How innovative or unique is it?
4. Cost: What are the resource requirements?

Ideas with critiques:
{ideas_text}

Provide a ranked list from highest to lowest priority. For each idea, include:
- The original idea
- Its critique
- Priority score (1-10)
- Reasoning for the ranking

Format as a numbered list with clear priority rankings."""

        try:
            # Use Google Generative AI to prioritize ideas
            response = self.model.generate_content(prompt)
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            # Parse the response to extract prioritized ideas
            prioritized_ideas = self._parse_prioritized_ideas(response_text, ideas_with_critiques)
            
            return {
                "prioritized_ideas": prioritized_ideas,
                "count": len(prioritized_ideas)
            }
        except Exception as e:
            # Fallback: return original ideas in order
            return {
                "prioritized_ideas": ideas_with_critiques,
                "count": len(ideas_with_critiques),
                "error": str(e)
            }
    
    def _parse_prioritized_ideas(self, response: str, original_ideas: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Parse prioritized ideas from the agent's response.
        
        Args:
            response: The agent's text response
            original_ideas: Original list of ideas with critiques
            
        Returns:
            List of prioritized ideas with rankings
        """
        # Simple parsing: try to extract priority information
        # For now, return the original ideas with the response as additional info
        prioritized = []
        for idx, item in enumerate(original_ideas):
            prioritized.append({
                "rank": idx + 1,
                "idea": item.get("idea", ""),
                "critique": item.get("critique", ""),
                "prioritization_notes": response  # Include full response as notes
            })
        
        return prioritized
    
    async def prioritize_ideas(self, ideas_with_critiques: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Prioritize ideas based on criteria.
        
        Args:
            ideas_with_critiques: List of ideas with their critiques
            
        Returns:
            Dictionary containing prioritized ideas
        """
        return self._prioritize_ideas_impl(ideas_with_critiques)

