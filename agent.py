import asyncio
import json
import re
import logging
import vertexai
from google.cloud import secretmanager
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration, Part, GenerationConfig
from memory import AsyncMemoryManager
from tools import lookup_gcp_service, get_cost_estimate

# Set up basic terminal logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [ORCHESTRATOR] - %(message)s")
logger = logging.getLogger(__name__)

# ==========================================
# 0. SECURITY & SECRET MANAGEMENT UTILITIES
# ==========================================
def get_secret(project_id: str, secret_id: str, version_id: str = "latest") -> str:
    """
    Dynamically retrieves a secret payload from Google Secret Manager.
    Fails gracefully with a fallback warning if the secret or permission is missing.
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.warning(f"[SECURITY WARNING] Could not retrieve secret '{secret_id}': {e}")
        return ""

# ==========================================
# 1. TOOL SCHEMAS
# ==========================================
lookup_func = FunctionDeclaration(
    name="lookup_gcp_service",
    description="Looks up details about a specific GCP service. Use this when the user asks what a service does.",
    parameters={
        "type": "object",
        "properties": {
            "service_name": {"type": "string", "description": "The exact name of the GCP service, e.g., 'Compute Engine'."}
        },
        "required": ["service_name"]
    }
)

cost_estimate_func = FunctionDeclaration(
    name="get_cost_estimate",
    description="Calculates cost estimates for a GCP service. This is a high-stakes tool.",
    parameters={
        "type": "object",
        "properties": {
            "service_name": {"type": "string", "description": "The name of the GCP service to estimate."},
            "usage_tier": {"type": "string", "description": "The volume tier of usage. Must strictly be one of: 'Low', 'Medium', 'High'."}
        },
        "required": ["service_name", "usage_tier"]
    }
)

# ==========================================
# 2. ORCHESTRATOR CLASS
# ==========================================
class FDEOrchestrator:
    """Enterprise Multi-Agent Orchestrator for Google Cloud FDE Architecture."""
    
    def __init__(self, project_id: str, session_id: str = "default_session"):
        logger.info(f"Initializing Vertex AI Orchestrator for project: {project_id}, session: {session_id}...")
        vertexai.init(project=project_id, location="us-central1")
        
        self.memory = AsyncMemoryManager(session_id=session_id, max_messages=10)
        
        # 🚦 The Router Agent (Fast, strict schema)
        self.router_model = GenerativeModel(
            "gemini-2.5-flash",
            system_instruction="You are an intent router. Classify the user's intent into exactly one of three categories: 'FINANCE' (cost/pricing), 'RESEARCH' (GCP service queries), or 'GENERAL' (greetings/other)."
        )
        
        # 🧠 The Specialist Agents
        self.architect_agent = GenerativeModel(
            "gemini-2.5-flash",
            tools=[Tool(function_declarations=[lookup_func])],
            system_instruction="You are a Cloud Architect. Use your lookup tool to provide factual details about GCP services."
        )
        
        self.finance_agent = GenerativeModel(
            "gemini-2.5-flash", 
            tools=[Tool(function_declarations=[cost_estimate_func])],
            system_instruction="You are a FinOps Agent. Use your cost tool to generate pricing estimates. Never estimate without the tool."
        )
        
        self.general_agent = GenerativeModel(
            "gemini-2.5-flash",
            system_instruction="You are a helpful Google Cloud FDE assistant. Answer general questions directly."
        )

    def _security_guardrail(self, text: str) -> bool:
        """🛡️ Layer 1: Heuristic Guardrail to catch basic prompt injections."""
        forbidden_patterns = [r"(?i)ignore (all )?previous instructions", r"(?i)system prompt", r"(?i)bypass"]
        for pattern in forbidden_patterns:
            if re.search(pattern, text):
                logger.warning("Security Guardrail triggered: Potential prompt injection detected.")
                return False
        return True

    async def _route_intent(self, user_input: str) -> str:
        """🚦 Layer 2: Determine which specialist handles the request."""
        routing_prompt = f"Classify this input: '{user_input}'"
        config = GenerationConfig(response_mime_type="application/json")
        try:
            response = self.router_model.generate_content(routing_prompt, generation_config=config)
            intent = response.text.upper()
            if "FINANCE" in intent: return "FINANCE"
            if "RESEARCH" in intent: return "RESEARCH"
            return "GENERAL"
        except Exception as e:
            logger.error(f"Routing failed, defaulting to GENERAL: {e}")
            return "GENERAL"

    async def process_request(self, user_input: str) -> dict:
        """Main execution loop for user requests."""
        logger.info(f"Processing new message: '{user_input}'")
        
        # Layer 1: Run Guardrails
        if not self._security_guardrail(user_input):
            return {"status": "error", "message": "Request blocked by security policy."}
            
        await self.memory.add_message(role="user", content=user_input)
        
        # Layer 2: Routing
        intent = await self._route_intent(user_input)
        logger.info(f"Router classified intent as: {intent}")
        
        # Layer 3: Dispatch to Specialist
        if intent == "FINANCE":
            active_model = self.finance_agent
        elif intent == "RESEARCH":
            active_model = self.architect_agent
        else:
            active_model = self.general_agent

        # Reconstruct chat session with history for the selected agent
        history = await self.memory.get_formatted_history()
        vertex_history = [Part.from_text(msg["content"]) for msg in history if msg["role"] in ["user", "assistant"]]
        
        self.current_chat = active_model.start_chat()
        
        try:
            response = self.current_chat.send_message(user_input)
            
            # Intercept Tool Calls
            if response.candidates and response.candidates[0].function_calls:
                func_call = response.candidates[0].function_calls[0]
                func_name = func_call.name
                args_dict = {key: value for key, value in func_call.args.items()}
                
                # High-Stakes Guardrail Validation
                if func_name == "get_cost_estimate":
                    logger.info(f"Guardrail triggered! Pausing execution for high-stakes tool: {func_name}")
                    return {
                        "status": "requires_approval",
                        "function_name": func_name,
                        "arguments": args_dict,
                        "message": f"Tool '{func_name}' requires explicit HITL approval."
                    }
                
                # Low-Stakes Execution
                logger.info(f"Executing low-stakes tool '{func_name}'...")
                return await self.execute_and_reply(func_name, args_dict)
                
            else:
                reply = response.text
                await self.memory.add_message(role="assistant", content=reply)
                return {"status": "success", "reply": reply}
                
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {"status": "error", "message": str(e)}

    async def execute_and_reply(self, func_name: str, args_dict: dict) -> dict:
        """Executes the tool and passes the result back to the specific agent."""
        try:
            args_json = json.dumps(args_dict)
            if func_name == "lookup_gcp_service":
                tool_result = lookup_gcp_service(args_json)
            elif func_name == "get_cost_estimate":
                tool_result = get_cost_estimate(args_json)
            else:
                raise ValueError(f"Unknown tool: {func_name}")
                
            await self.memory.add_message(role="tool", content=tool_result)
            
            logger.info(f"Sending {func_name} result back to specialist...")
            final_response = self.current_chat.send_message(
                Part.from_function_response(name=func_name, response={"content": tool_result})
            )
            
            reply = final_response.text
            await self.memory.add_message(role="assistant", content=reply)
            return {"status": "success", "reply": reply}
            
        except Exception as e:
            logger.error(f"Error executing tool: {e}")
            return {"status": "error", "message": str(e)}
