import asyncio
import json
import vertexai
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration, Part
from memory import AsyncMemoryManager
from tools import lookup_gcp_service, get_cost_estimate

import logging

# Set up basic terminal logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [AGENT] - %(message)s")
logger = logging.getLogger(__name__)

# Define Vertex AI Tool Schemas
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

fde_tools = Tool(function_declarations=[lookup_func, cost_estimate_func])

class FDEAgent:
    """Enterprise-grade, stateless-compatible Google Cloud FDE Architecture Assistant."""
    
    def __init__(self, project_id: str, session_id: str = "default_session"):
        logger.info(f"Initializing Vertex AI for project: {project_id}, session: {session_id}...")
        vertexai.init(project=project_id, location="us-central1")
        
        self.model = GenerativeModel(
            "gemini-2.5-flash", 
            tools=[fde_tools],
            system_instruction="You are an expert Google Cloud FDE Assistant. Answer questions, but if the user asks about GCP services or costs, use your tools to look up the exact data. Never guess."
        )
        self.chat = self.model.start_chat()
        self.memory = AsyncMemoryManager(session_id=session_id, max_messages=10)
        
    async def process_request(self, user_input: str) -> dict:
        """Processes a user request and handles non-blocking tool matching."""
        logger.info(f"Processing new message: '{user_input}'")
        await self.memory.add_message(role="user", content=user_input)
        
        try:
            response = self.chat.send_message(user_input)
            
            # Check if Gemini wants to call a tool
            if response.candidates and response.candidates[0].function_calls:
                func_call = response.candidates[0].function_calls[0]
                func_name = func_call.name
                args_dict = {key: value for key, value in func_call.args.items()}
                
                # Check for high-stakes tool requiring HITL approval
                if func_name == "get_cost_estimate":
                    logger.info(f"Guardrail triggered! Pausing execution for tool: {func_name}")
                    return {
                        "status": "requires_approval",
                        "function_name": func_name,
                        "arguments": args_dict,
                        "message": f"Tool '{func_name}' requires approval before executing."
                    }
                
                # Low-stakes tool: Execute automatically
                logger.info(f"Low-stakes tool '{func_name}' matched. Executing automatically.")
                return await self.execute_and_reply(func_name, args_dict)
                
            else:
                logger.info("No tools required. Returning standard response.")
                reply = response.text
                await self.memory.add_message(role="assistant", content=reply)
                return {"status": "success", "reply": reply}
                
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {"status": "error", "message": str(e)}

    async def execute_and_reply(self, func_name: str, args_dict: dict) -> dict:
        """Executes a tool and returns the final synthesized reply from the model."""
        logger.info(f"Executing tool '{func_name}' with args: {args_dict}")
        try:
            args_json = json.dumps(args_dict)
            
            if func_name == "lookup_gcp_service":
                tool_result = lookup_gcp_service(args_json)
            elif func_name == "get_cost_estimate":
                tool_result = get_cost_estimate(args_json)
            else:
                raise ValueError(f"Unknown tool: {func_name}")
                
            await self.memory.add_message(role="tool", content=tool_result)
            
            # Feed tool result back to the model turn
            logger.info("Sending tool result back to Vertex AI...")
            final_response = self.chat.send_message(
                Part.from_function_response(
                    name=func_name,
                    response={"content": tool_result}
                )
            )
            reply = final_response.text
            await self.memory.add_message(role="assistant", content=reply)
            logger.info("Final response generated successfully.")
            return {"status": "success", "reply": reply}
            
        except Exception as e:
            logger.error(f"Error executing tool: {e}")
            return {"status": "error", "message": str(e)}
