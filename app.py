import streamlit as st
import asyncio
import os
import json
from agent import FDEOrchestrator

# --- Config ---
st.set_page_config(page_title="Multi-Agent FDE", page_icon="☁️", layout="wide")

st.title("☁️ Google Cloud FDE Blueprint Agent")
st.markdown("An enterprise AI orchestrator acting as a **Cloud Architect** and **FinOps Analyst**. Try asking for a cost estimate to see the HITL guardrails!")

# --- Helper to manage async loop elegantly in Streamlit ---
def run_async(coroutine):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        return asyncio.run_coroutine_threadsafe(coroutine, loop).result()
    else:
        return asyncio.run(coroutine)

# --- Session State Initialization ---
if "agent" not in st.session_state:
    project_id = os.getenv("GCP_PROJECT_ID", "vital-octagon-19612") 
    st.session_state.agent = FDEOrchestrator(project_id=project_id, session_id="streamlit_demo_session")
    
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I am your Multi-Agent FDE Assistant. I can route to an Architect or FinOps specialist. How can I help?"}]

# --- Render Chat History ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        if "trace" in msg and msg["trace"]:
            with st.expander("🛠️ Observability Trace Metadata"):
                st.json(msg["trace"])

# --- HITL (Human-in-the-Loop) State Check ---
if st.session_state.get("awaiting_approval"):
    st.warning("⚠️ High-Stakes Tool Execution Stopped: Requires Human Approval")
    cols = st.columns(2)
    func_name = st.session_state.pending_tool["function_name"]
    args_dict = st.session_state.pending_tool["arguments"]
    
    st.info(f"**Tool Invocation:** `{func_name}`")
    st.json(args_dict)
    
    with cols[0]:
        if st.button("✅ Approve Tool Execution", use_container_width=True):
            with st.spinner("Executing tool and synthesizing response..."):
                # Execute the tool via our orchestrator which will run the actual tool code
                response = run_async(st.session_state.agent.execute_and_reply(func_name, args_dict))
                if response.get("status") == "success":
                    st.session_state.messages.append({"role": "assistant", "content": response["reply"]})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": f"Error: {response.get('message')}"})
            st.session_state.awaiting_approval = False
            st.rerun()

    with cols[1]:
        if st.button("❌ Reject", use_container_width=True):
            st.session_state.messages.append({"role": "assistant", "content": "Tool execution was rejected by the human supervisor."})
            st.session_state.awaiting_approval = False
            st.rerun()

# --- Main Chat Input ---
elif user_message := st.chat_input("Ask me about GCP services or for a cost estimate..."):
    st.session_state.messages.append({"role": "user", "content": user_message})
    with st.chat_message("user"):
        st.markdown(user_message)
        
    with st.chat_message("assistant"):
        with st.spinner("Analyzing intent and engaging multi-agent router..."):
            response = run_async(st.session_state.agent.process_request(user_message))
            
            if response.get("status") == "requires_approval":
                st.session_state.awaiting_approval = True
                st.session_state.pending_tool = response
                st.rerun()
            elif response.get("status") == "success":
                st.markdown(response["reply"])
                st.session_state.messages.append({"role": "assistant", "content": response["reply"]})
            else:
                err_msg = f"Error: {response.get('message')}"
                st.markdown(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})
