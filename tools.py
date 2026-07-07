import json

def lookup_gcp_service(args_json: str) -> str:
    """Mock database lookup for GCP services (Low Stakes)."""
    print(f"\n[Tool Execution] Running lookup_gcp_service with args: {args_json}")
    args = json.loads(args_json)
    service_name = args.get("service_name", "").lower()

    # A mock internal database of services
    mock_db = {
        "compute engine": "Google Compute Engine (GCE) provides highly customizable virtual machines.",
        "cloud storage": "Google Cloud Storage (GCS) is a highly durable, enterprise-grade object storage service.",
        "cloud run": "Cloud Run is a managed compute platform that lets you run containers directly on top of Google's scalable infrastructure.",
        "spanner": "Cloud Spanner is a fully managed, mission-critical, relational database service that offers transactional consistency at global scale."
    }

    # Search our mock DB
    for key, description in mock_db.items():
        if key in service_name:
            return json.dumps({
                "service": service_name, 
                "internal_description": description, 
                "status": "found_in_internal_db"
            })

    return json.dumps({
        "service": service_name, 
        "internal_description": "Service not found in internal FDE database. Rely on general knowledge.", 
        "status": "not_found"
    })

def get_cost_estimate(args_json: str) -> str:
    """Mock cost estimator (High Stakes - Requires Approval)."""
    print(f"\n[Tool Execution] Running get_cost_estimate with args: {args_json}")
    args = json.loads(args_json)
    service_name = args.get("service_name", "Unknown")
    usage_tier = args.get("usage_tier", "Low")

    # Mock cost calculation logic
    tier_multipliers = {"Low": 50, "Medium": 500, "High": 5000}
    estimated_cost = tier_multipliers.get(usage_tier, 0)

    return json.dumps({
        "service": service_name,
        "usage_tier": usage_tier,
        "estimated_monthly_cost_usd": estimated_cost,
        "notes": "Internal FDE estimate. Final pricing may vary based on region."
    })
