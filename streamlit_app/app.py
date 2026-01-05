"""Streamlit UI for the Multi-Agent Brainstorming System."""
import streamlit as st
import os
import asyncio
import json
import html
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import httpx


load_dotenv(dotenv_path="../.env")

# Page configuration
st.set_page_config(
    page_title="Product Development System",
    page_icon="💡",
    layout="wide"
)

# Configuration defaults
DEFAULT_HOST_AGENT_URL = os.getenv("HOST_AGENT_URL", "https://devagentguard.vigilnz.com/agent")
DEFAULT_ARCHITECT_AGENT_URL = os.getenv("ARCHITECT_AGENT_URL", "http://localhost:9991")
DEFAULT_DEVELOPER_AGENT_URL = os.getenv("DEVELOPER_AGENT_URL", "http://localhost:9992")
DEFAULT_TESTER_AGENT_URL = os.getenv("TESTER_AGENT_URL", "http://localhost:9993")


def send_development_request(user_request: str, host_agent_url: str, architect_agent_url: str = None, 
                               developer_agent_url: str = None, tester_agent_url: str = None) -> Dict[str, Any]:
    """
    Send a development request to the host agent using REST API.
    """
    async def _send_request():
        try:
            async with httpx.AsyncClient(timeout=300) as http_client:
                # Prepare request payload with optional agent URLs
                payload = {"user_request": user_request}
                if architect_agent_url:
                    payload["architect_agent_url"] = architect_agent_url
                if developer_agent_url:
                    payload["developer_agent_url"] = developer_agent_url
                if tester_agent_url:
                    payload["tester_agent_url"] = tester_agent_url
                
                # Step 1: Create task by sending POST request
                create_response = await http_client.post(
                    f"{host_agent_url}/api/develop",
                    json=payload,
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
                        f"{host_agent_url}/api/develop/{task_id}"
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
                                "name": "development_result",
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
        
        # Find the development result artifact
        development_data = None
        for artifact in artifacts:
            if artifact.get("name") == "development_result" and "parsed_content" in artifact:
                development_data = artifact["parsed_content"]
                break
        
        if development_data:
            # Display user request
            if "user_request" in development_data:
                st.subheader(f"📌 Project Request: {development_data['user_request']}")
            
            # Display status
            status = development_data.get("status", "unknown")
            if status == "success":
                st.success("✅ Successfully completed product development workflow!")
            else:
                st.error(f"❌ Status: {status}")
                message = development_data.get("message", "Unknown error")
                st.error(f"**Error Details:** {message}")
                # Special handling for quota errors
                if "quota" in message.lower() or "429" in message:
                    st.warning("💡 **Tip:** API quota limits have been reached. Please wait a few minutes and try again.")
                return
            
            # Display workflow ID
            if "workflow_id" in development_data:
                st.caption(f"Workflow ID: {development_data['workflow_id'][:8]}...")
            
            # Download button for results
            json_str = json.dumps(development_data, indent=2)
            st.download_button(
                label="📥 Download Results as JSON",
                data=json_str,
                file_name=f"development_results_{development_data.get('workflow_id', 'unknown')[:8]}.json",
                mime="application/json"
            )
            
            st.divider()
            
            # Display Architectural Plan
            if "plan" in development_data:
                st.subheader("🏗️ Architectural Plan")
                plan = development_data["plan"]
                if isinstance(plan, dict):
                    st.json(plan)
                else:
                    st.text(str(plan))
                st.divider()
            
            # Display Code Implementation
            if "code" in development_data:
                st.subheader("💻 Code Implementation")
                code = development_data["code"]
                if isinstance(code, dict):
                    if "files" in code:
                        st.markdown(f"**Summary:** {code.get('summary', 'N/A')}")
                        st.markdown(f"**Total Files:** {len(code.get('files', []))}")
                        for file_info in code.get("files", []):
                            with st.expander(f"📄 {file_info.get('path', 'unknown')}"):
                                st.markdown(f"**Description:** {file_info.get('description', 'N/A')}")
                                st.code(file_info.get("content", ""), language="python")
                    else:
                        st.json(code)
                else:
                    st.text(str(code))
                st.divider()
            
            # Display Test Results
            if "test_results" in development_data:
                st.subheader("🧪 Test Results")
                test_results = development_data["test_results"]
                if isinstance(test_results, dict):
                    overall_status = test_results.get("overall_status", "unknown")
                    if overall_status == "pass":
                        st.success(f"✅ Overall Status: {overall_status.upper()}")
                    elif overall_status == "fail":
                        st.error(f"❌ Overall Status: {overall_status.upper()}")
                    else:
                        st.info(f"ℹ️ Overall Status: {overall_status.upper()}")
                    
                    st.markdown(f"**Test Summary:** {test_results.get('test_summary', 'N/A')}")
                    
                    if "test_cases" in test_results and test_results["test_cases"]:
                        st.markdown("**Test Cases:**")
                        for test_case in test_results["test_cases"]:
                            test_status = test_case.get("status", "unknown")
                            status_icon = "✅" if test_status == "pass" else "❌" if test_status == "fail" else "⚠️"
                            st.markdown(f"{status_icon} **{test_case.get('test_name', 'Unnamed Test')}**")
                            st.markdown(f"   *{test_case.get('description', 'No description')}*")
                            if test_case.get("details"):
                                st.text(test_case.get("details"))
                    
                    if "issues_found" in test_results and test_results["issues_found"]:
                        st.warning("**Issues Found:**")
                        for issue in test_results["issues_found"]:
                            st.markdown(f"- {issue}")
                    
                    if "recommendations" in test_results and test_results["recommendations"]:
                        st.info("**Recommendations:**")
                        for rec in test_results["recommendations"]:
                            st.markdown(f"- {rec}")
                else:
                    st.text(str(test_results))
        else:
            # Fallback: show raw artifacts
            st.warning("Could not parse development results. Showing raw data:")
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
    st.title("🚀Product Development System")
    st.markdown("Build products through AI agents: Architect → Developer → Tester")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Initialize session state for URLs if not present
        if "host_agent_url" not in st.session_state:
            st.session_state.host_agent_url = DEFAULT_HOST_AGENT_URL
        if "architect_agent_url" not in st.session_state:
            st.session_state.architect_agent_url = DEFAULT_ARCHITECT_AGENT_URL
        if "developer_agent_url" not in st.session_state:
            st.session_state.developer_agent_url = DEFAULT_DEVELOPER_AGENT_URL
        if "tester_agent_url" not in st.session_state:
            st.session_state.tester_agent_url = DEFAULT_TESTER_AGENT_URL
        
        # Host Agent URL
        st.session_state.host_agent_url = st.text_input(
            "Host Agent URL",
            value=st.session_state.host_agent_url,
            help="URL of the host agent (Product Owner/Orchestrator)",
            key="host_agent_url_input"
        )
        
        st.divider()
        st.subheader("Remote Agent URLs")
        
        # Architect Agent URL
        st.session_state.architect_agent_url = st.text_input(
            "Architect Agent URL",
            value=st.session_state.architect_agent_url,
            help="URL of the architect agent",
            key="architect_agent_url_input"
        )
        
        # Developer Agent URL
        st.session_state.developer_agent_url = st.text_input(
            "Developer Agent URL",
            value=st.session_state.developer_agent_url,
            help="URL of the developer agent",
            key="developer_agent_url_input"
        )
        
        # Tester Agent URL
        st.session_state.tester_agent_url = st.text_input(
            "Tester Agent URL",
            value=st.session_state.tester_agent_url,
            help="URL of the tester agent",
            key="tester_agent_url_input"
        )
        
        st.divider()
        st.markdown("### About")
        st.markdown("""
        This system uses multiple AI agents:
        - **Architect**: Creates architectural plans
        - **Developer**: Builds code implementation
        - **Tester**: Tests the code and provides results
        """)
    
    # Main content area
    st.header("Enter Your Project Request")
    
    user_request = st.text_area(
        "What would you like to build?",
        placeholder="e.g., Build a simple calculator application",
        height=100
    )
    
    if st.button("🚀 Start Development", type="primary", use_container_width=True):
        if not user_request or not user_request.strip():
            st.error("Please enter a project request.")
            return
        
        # Show progress
        with st.spinner("Processing your request..."):
            # Send request to host agent with configured URLs
            result = send_development_request(
                user_request.strip(),
                st.session_state.host_agent_url,
                st.session_state.architect_agent_url,
                st.session_state.developer_agent_url,
                st.session_state.tester_agent_url
            )
        
        # Display results
        display_results(result)
    
    # Display example
    with st.expander("💡 Example Project Requests"):
        st.markdown("""
        - Build a simple calculator application
        - Create a todo list web app
        - Develop a weather dashboard
        - Build a chat application
        - Create a file manager application
        """)


if __name__ == "__main__":
    main()
