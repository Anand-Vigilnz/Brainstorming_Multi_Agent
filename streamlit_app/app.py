"""Streamlit UI for the Multi-Agent Brainstorming System."""
import streamlit as st
import httpx
import os
from typing import Dict, Any


# Page configuration
st.set_page_config(
    page_title="Multi-Agent Brainstorming System",
    page_icon="💡",
    layout="wide"
)

# Configuration
HOST_AGENT_URL = os.getenv("HOST_AGENT_URL", "http://localhost:9999")


def send_brainstorming_request(topic: str) -> Dict[str, Any]:
    """
    Send a brainstorming request to the host agent.
    
    Args:
        topic: The brainstorming topic
        
    Returns:
        Response from the host agent
    """
    try:
        with httpx.Client(timeout=300.0) as client:
            response = client.post(
                f"{HOST_AGENT_URL}/task",
                json={
                    "skill": "brainstorm",
                    "input": {"topic": topic}
                }
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        return {"status": "error", "message": f"Connection error: {str(e)}"}
    except httpx.HTTPStatusError as e:
        return {"status": "error", "message": f"HTTP error: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Error: {str(e)}"}


def main():
    """Main Streamlit application."""
    st.title("💡 Multi-Agent Brainstorming System")
    st.markdown("Generate, critique, and prioritize ideas using AI agents")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        host_agent_url = st.text_input(
            "Host Agent URL",
            value=HOST_AGENT_URL,
            help="URL of the host agent (orchestrator)"
        )
        st.divider()
        st.markdown("### About")
        st.markdown("""
        This system uses multiple AI agents:
        - **Idea Generator**: Creates innovative ideas
        - **Critic**: Evaluates ideas for feasibility
        - **Prioritizer**: Ranks ideas by importance
        """)
    
    # Main content area
    st.header("Enter Your Brainstorming Topic")
    
    topic = st.text_area(
        "What would you like to brainstorm?",
        placeholder="e.g., Ways to improve remote team collaboration",
        height=100
    )
    
    if st.button("🚀 Generate Ideas", type="primary", use_container_width=True):
        if not topic or not topic.strip():
            st.error("Please enter a brainstorming topic.")
            return
        
        # Show progress
        with st.spinner("Processing your request..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Step 1: Generating ideas
            status_text.text("Step 1/3: Generating ideas...")
            progress_bar.progress(33)
            
            # Send request to host agent
            result = send_brainstorming_request(topic.strip())
            
            # Step 2: Critiquing ideas
            status_text.text("Step 2/3: Critiquing ideas...")
            progress_bar.progress(66)
            
            # Step 3: Prioritizing ideas
            status_text.text("Step 3/3: Prioritizing ideas...")
            progress_bar.progress(100)
            
            status_text.empty()
            progress_bar.empty()
        
        # Display results
        # Handle both old nested format and new direct format
        if result.get("status") == "success":
            # Direct format (new)
            prioritized_ideas = result.get("prioritized_ideas", [])
            total_ideas = result.get("total_ideas", 0)
            result_topic = result.get("topic", topic.strip())
        elif result.get("status") == "completed" and result.get("output", {}).get("status") == "success":
            # Nested format (old - for backward compatibility)
            output = result.get("output", {})
            prioritized_ideas = output.get("prioritized_ideas", [])
            total_ideas = output.get("total_ideas", 0)
            result_topic = output.get("topic", topic.strip())
            result = output  # Use the nested output as the main result
        else:
            # Error case
            prioritized_ideas = []
            total_ideas = 0
            result_topic = topic.strip()
        
        if result.get("status") == "success" or (result.get("status") == "completed" and result.get("output", {}).get("status") == "success"):
            st.success("✅ Brainstorming complete!")
            
            # Display summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Ideas Generated", total_ideas)
            with col2:
                st.metric("Ideas Prioritized", len(prioritized_ideas))
            with col3:
                st.metric("Topic", result_topic[:30] + "..." if len(result_topic) > 30 else result_topic)
            
            if prioritized_ideas:
                st.header("📊 Prioritized Ideas")
                
                # Create tabs for better organization
                tab1, tab2 = st.tabs(["📋 Summary View", "📄 Detailed View"])
                
                with tab1:
                    # Summary view with cards
                    for idx, idea_data in enumerate(prioritized_ideas, 1):
                        rank = idea_data.get('rank', idx)
                        idea = idea_data.get('idea', 'N/A')
                        critique = idea_data.get('critique', 'N/A')
                        
                        # Truncate long text for summary
                        idea_short = idea[:100] + "..." if len(idea) > 100 else idea
                        critique_short = critique[:200] + "..." if len(critique) > 200 else critique
                        
                        with st.container():
                            st.subheader(f"🥇 Rank #{rank}: {idea_short}")
                            st.markdown(f"**Full Idea:** {idea}")
                            
                            with st.expander("📝 View Critique", expanded=False):
                                st.markdown(critique)
                            
                            st.divider()
                
                with tab2:
                    # Detailed view with all information
                    for idx, idea_data in enumerate(prioritized_ideas, 1):
                        rank = idea_data.get('rank', idx)
                        idea = idea_data.get('idea', 'N/A')
                        critique = idea_data.get('critique', 'N/A')
                        
                        with st.expander(f"Rank #{rank}: {idea[:60]}...", expanded=(idx == 1)):
                            st.markdown("### 💡 Idea")
                            st.info(idea)
                            
                            st.markdown("### 🔍 Critique")
                            st.markdown(critique)
                            
                            if 'prioritization_notes' in idea_data and idea_data['prioritization_notes']:
                                st.markdown("### 📊 Prioritization Analysis")
                                # Show only a portion of prioritization notes to avoid repetition
                                notes = idea_data['prioritization_notes']
                                # Try to extract just the relevant part for this idea
                                if f"**Idea:** {idea}" in notes or f"*{idea}" in notes:
                                    # Find the section for this specific idea
                                    st.markdown(notes[:1000] + "..." if len(notes) > 1000 else notes)
                                else:
                                    st.caption("Full prioritization analysis available in summary")
                            
                            st.caption(f"Priority Rank: {rank}")
            else:
                st.warning("No prioritized ideas were returned.")
        else:
            # Show error details
            error_message = result.get("message", "Unknown error occurred")
            
            # Check if it's the nested format with actual data
            if result.get("status") == "completed" and "output" in result:
                output = result.get("output", {})
                if output.get("status") == "success":
                    # Data is actually there, just in nested format
                    st.warning("⚠️ Response format issue detected. Data found in nested format.")
                    prioritized_ideas = output.get("prioritized_ideas", [])
                    total_ideas = output.get("total_ideas", 0)
                    result_topic = output.get("topic", topic.strip())
                    
                    # Display the data
                    st.success("✅ Brainstorming complete!")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Ideas Generated", total_ideas)
                    with col2:
                        st.metric("Ideas Prioritized", len(prioritized_ideas))
                    with col3:
                        st.metric("Topic", result_topic[:30] + "..." if len(result_topic) > 30 else result_topic)
                    
                    if prioritized_ideas:
                        st.header("📊 Prioritized Ideas")
                        tab1, tab2 = st.tabs(["📋 Summary View", "📄 Detailed View"])
                        
                        with tab1:
                            for idx, idea_data in enumerate(prioritized_ideas, 1):
                                rank = idea_data.get('rank', idx)
                                idea = idea_data.get('idea', 'N/A')
                                critique = idea_data.get('critique', 'N/A')
                                idea_short = idea[:100] + "..." if len(idea) > 100 else idea
                                
                                with st.container():
                                    st.subheader(f"🥇 Rank #{rank}: {idea_short}")
                                    st.markdown(f"**Full Idea:** {idea}")
                                    with st.expander("📝 View Critique", expanded=False):
                                        st.markdown(critique)
                                    st.divider()
                        
                        with tab2:
                            for idx, idea_data in enumerate(prioritized_ideas, 1):
                                rank = idea_data.get('rank', idx)
                                idea = idea_data.get('idea', 'N/A')
                                critique = idea_data.get('critique', 'N/A')
                                
                                with st.expander(f"Rank #{rank}: {idea[:60]}...", expanded=(idx == 1)):
                                    st.markdown("### 💡 Idea")
                                    st.info(idea)
                                    st.markdown("### 🔍 Critique")
                                    st.markdown(critique)
                                    if 'prioritization_notes' in idea_data:
                                        st.markdown("### 📊 Prioritization Analysis")
                                        notes = idea_data['prioritization_notes']
                                        st.markdown(notes[:1000] + "..." if len(notes) > 1000 else notes)
                                    st.caption(f"Priority Rank: {rank}")
                    return
            
            # Actual error case
            st.error(f"❌ Error: {error_message}")
            with st.expander("🔍 View Error Details", expanded=False):
                st.json(result)
    
    # Display example
    with st.expander("💡 Example Topics"):
        st.markdown("""
        - Ways to reduce carbon footprint in daily life
        - Innovative features for a mobile app
        - Strategies to improve employee engagement
        - New product ideas for a tech startup
        - Solutions for urban transportation challenges
        """)


if __name__ == "__main__":
    main()

