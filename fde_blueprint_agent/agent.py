from google.adk import agents

# --- 1. Local Data Mocks ---
GCP_CATALOG = {
    "compute": "Cloud Run for containerized apps.",
    "database": "Cloud SQL for relational data.",
    "storage": "Cloud Storage for unstructured blobs."
}

MOCK_COSTS = {
    "Cloud Run": "Starts at $0 (generous free tier), then pay-per-use.",
    "Cloud SQL": "Starts around $10/month for a small shared-core instance.",
    "Cloud Storage": "Standard storage is roughly $0.02 per GB/month."
}

# --- 2. Tools ---
def lookup_gcp_service(requirement_type: str) -> str:
    """Looks up recommended Google Cloud services based on the requirement type ('compute', 'database', or 'storage')."""
    category = requirement_type.lower().strip()
    if category in GCP_CATALOG:
        return GCP_CATALOG[category]
    return "Error: Unknown category."

def get_cost_estimate(service_name: str) -> str:
    """Gets the estimated starting cost for a specific Google Cloud service."""
    for service, cost in MOCK_COSTS.items():
        if service.lower() in service_name.lower():
            return cost
    return "Cost estimate not available for this service."

# --- 3. The Agent (Now with Orchestration Logic) ---
agent = agents.LlmAgent(
    name="fde_blueprint_agent",
    model="gemini-flash-latest",
    instruction=(
        "You are a Google Cloud FDE Architecture Assistant. "
        "When a user asks for a recommendation, you must follow this 2-step orchestration process: "
        "Step 1: Use the 'lookup_gcp_service' tool to find the right service. "
        "Step 2: Take the service name from Step 1 and use the 'get_cost_estimate' tool to find its pricing. "
        "Finally, formulate a professional response that includes both the recommended service and its estimated cost."
    ),
    tools=[lookup_gcp_service, get_cost_estimate]
)

root_agent = agent
