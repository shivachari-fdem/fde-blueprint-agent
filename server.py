from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import uvicorn
import os

# Import the new Multi-Agent Orchestrator
from agent import FDEOrchestrator 

app = FastAPI(title="Multi-Tenant FDE Blueprint Agent")

# Track active orchestrator instances per session
sessions: Dict[str, FDEOrchestrator] = {}

# --- IMPORTANT: Replace this with your actual Google Cloud Project ID! ---
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "vital-octagon-19612")

class InitRequest(BaseModel):
    session_id: str

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ApproveRequest(BaseModel):
    session_id: str
    approve: bool
    function_name: str
    arguments: Dict[str, Any]

def get_agent(session_id: str) -> FDEOrchestrator:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found. Please call /init first.")
    return sessions[session_id]

@app.post("/init")
def init_agent(request: InitRequest):
    # FIX: Updated to use FDEOrchestrator and corrected variable to PROJECT_ID
    sessions[request.session_id] = FDEOrchestrator(project_id=PROJECT_ID, session_id=request.session_id)
    return {"status": "success", "message": f"Agent initialized for session {request.session_id}"}

@app.post("/chat")
async def chat(request: ChatRequest):
    agent = get_agent(request.session_id)
    # Orchestrator uses route_and_process or process_request depending on exact implementation
    response = await agent.process_request(request.message) 
    return response

@app.post("/approve")
async def approve_tool(request: ApproveRequest):
    agent = get_agent(request.session_id)
    
    if request.approve:
        response = await agent.execute_and_reply(request.function_name, request.arguments)
        return response
    else:
        return {"status": "rejected", "message": "Tool execution was rejected by supervisor."}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
