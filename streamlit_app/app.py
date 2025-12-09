"""Streamlit UI for the Multi-Agent Brainstorming System."""
import streamlit as st
import os
import asyncio
import json
import html
from typing import Dict, Any

import httpx


# Page configuration
st.set_page_config(
    page_title="Multi-Agent Brainstorming System",
    page_icon="💡",
    layout="wide"
)

# Configuration
# HOST_AGENT_URL = os.getenv("HOST_AGENT_URL", "http://localhost:9999")
# HOST_AGENT_URL = os.getenv("HOST_AGENT_URL", "http://localhost:9999")
HOST_AGENT_URL = "https://devagentguard.vigilnz.com/agent"


def send_brainstorming_request(topic: str) -> Dict[str, Any]:
    """
    Send a brainstorming request to the host agent using REST API.
    """
    async def _send_request():
        try:
            async with httpx.AsyncClient(timeout=300) as http_client:
                # Step 1: Create task by sending POST request
                create_response = await http_client.post(
                    f"{HOST_AGENT_URL}/api/brainstorm",
                    json={"topic": topic},
                    headers={"Content-Type": "application/json"}
                )
                create_response.raise_for_status()
                create_data = create_response.json()
                task_id = create_data.get("task_id")
                
                if not task_id:
                    return {"status": "error", "message": "No task_id received from host agent"}
                
                # Step 2: Poll for task completion
                max_polls = 120  # Poll for up to 2 minutes (120 * 1 second)
                poll_interval = 1  # Poll every 1 second
                
                for poll_count in range(max_polls):
                    await asyncio.sleep(poll_interval)
                    
                    # Get task status
                    status_response = await http_client.get(
                        f"{HOST_AGENT_URL}/api/brainstorm/{task_id}"
                    )
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    
                    task_status = status_data.get("status")
                    
                    if task_status == "completed":
                        # Task completed, extract result
                        result = status_data.get("result", {})
                        
                        # Format result to match expected display format
                        # Wrap result in artifacts format for display_results compatibility
                        return {
                            "status": "success",
                            "artifacts": [{
                                "name": "brainstorming_result",
                                "parsed_content": result
                            }]
                        }
                    elif task_status == "failed":
                        error = status_data.get("error", "Unknown error")
                        return {"status": "error", "message": error}
                    # If status is "pending" or "running", continue polling
                
                # Timeout
                return {"status": "error", "message": "Task timed out - polling exceeded maximum time"}

        except httpx.HTTPStatusError as e:
            return {"status": "error", "message": f"HTTP error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": f"Error: {str(e)}"}
    
    # Run async function in sync context
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_send_request())


def display_results(result: Dict[str, Any]):
    """Display results in an attractive format."""
    st.header("🎯 Results")
    
    # Check if we have artifacts with parsed content
    if result.get("status") == "success" and "artifacts" in result:
        artifacts = result["artifacts"]
        
        # Find the brainstorming result artifact
        brainstorming_data = None
        for artifact in artifacts:
            if artifact.get("name") == "brainstorming_result" and "parsed_content" in artifact:
                brainstorming_data = artifact["parsed_content"]
                break
        
        if brainstorming_data:
            # Display topic
            if "topic" in brainstorming_data:
                st.subheader(f"📌 Topic: {brainstorming_data['topic']}")
            
            # Display status
            status = brainstorming_data.get("status", "unknown")
            if status == "success":
                st.success("✅ Successfully generated and prioritized ideas!")
            else:
                st.error(f"❌ Status: {status}")
                message = brainstorming_data.get("message", "Unknown error")
                st.error(f"**Error Details:** {message}")
                # Special handling for quota errors
                if "quota" in message.lower() or "429" in message:
                    st.warning("💡 **Tip:** Google API quota limits have been reached. Please wait a few minutes and try again.")
                return
            
            # Display statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                total_ideas = brainstorming_data.get("total_ideas", 0)
                st.metric("Total Ideas Generated", total_ideas)
            with col2:
                prioritized_count = len(brainstorming_data.get("prioritized_ideas", []))
                st.metric("Prioritized Ideas", prioritized_count)
            with col3:
                if "workflow_id" in brainstorming_data:
                    st.caption(f"Workflow ID: {brainstorming_data['workflow_id'][:8]}...")
            
            # Download button for results
            json_str = json.dumps(brainstorming_data, indent=2)
            st.download_button(
                label="📥 Download Results as JSON",
                data=json_str,
                file_name=f"brainstorming_results_{brainstorming_data.get('workflow_id', 'unknown')[:8]}.json",
                mime="application/json"
            )
            
            st.divider()
            
            # Display prioritized ideas
            prioritized_ideas = brainstorming_data.get("prioritized_ideas", [])
            if prioritized_ideas:
                st.subheader("🏆 Prioritized Ideas")
                st.markdown("These ideas have been ranked by feasibility and impact:")
                
                for idx, idea_data in enumerate(prioritized_ideas, 1):
                    with st.container():
                        # Create a card-like container with different colors for each rank
                        colors = [
                            "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",  # Purple
                            "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",  # Pink
                            "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",  # Blue
                        ]
                        color = colors[(idx - 1) % len(colors)]
                        
                        st.markdown(f"""
                        <div style="
                            background: {color};
                            padding: 1.5rem;
                            border-radius: 10px;
                            margin-bottom: 1rem;
                            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                        ">
                            <h3 style="color: white; margin: 0 0 1rem 0;">#{idx} Top Priority</h3>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Idea content - handle both dict and string types
                        if isinstance(idea_data, dict):
                            idea_text = idea_data.get("idea", "")
                        elif isinstance(idea_data, str):
                            idea_text = idea_data
                        else:
                            idea_text = str(idea_data)
                        
                        if idea_text:
                            # Remove markdown bold markers and escape HTML
                            clean_idea = idea_text.replace("**", "").replace("*", "")
                            escaped_idea = html.escape(clean_idea)
                            st.markdown(f"""
                            <div style="
                                background-color: #f8f9fa;
                                padding: 1.5rem;
                                border-radius: 8px;
                                border-left: 4px solid #667eea;
                                margin-bottom: 1rem;
                            ">
                                <h4 style="color: #333; margin-top: 0;">💡 Idea</h4>
                                <p style="color: #555; font-size: 1.1em; line-height: 1.6;">{escaped_idea}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Rationale - only available if idea_data is a dict
                        if isinstance(idea_data, dict):
                            rationale = idea_data.get("rationale", "")
                        else:
                            rationale = ""
                        if rationale:
                            escaped_rationale = html.escape(rationale)
                            st.markdown(f"""
                            <div style="
                                background-color: #e8f5e9;
                                padding: 1.2rem;
                                border-radius: 8px;
                                border-left: 4px solid #4caf50;
                                margin-bottom: 1.5rem;
                            ">
                                <h4 style="color: #2e7d32; margin-top: 0;">📊 Rationale</h4>
                                <p style="color: #1b5e20; line-height: 1.6;">{escaped_rationale}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        if idx < len(prioritized_ideas):
                            st.divider()
            else:
                st.warning("No prioritized ideas found in the response.")
        else:
            # Fallback: show raw artifacts
            st.warning("Could not parse brainstorming results. Showing raw data:")
            st.json(result)
    elif result.get("status") == "error":
        st.error("❌ Error occurred")
        st.error(result.get("message", "Unknown error"))
        if "artifacts" in result:
            st.json(result)
    else:
        # Fallback: show raw result
        st.warning("Unexpected result format. Showing raw data:")
        st.json(result)


def main():
    """Main Streamlit application."""
    st.title("💡 Multi-Agent Brainstorming System")
    st.markdown("Generate, critique, and prioritize ideas using AI agents")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        st.text_input(
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
            # Send request to host agent
            result = send_brainstorming_request(topic.strip())
        
        # Display results
        display_results(result)
    
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
