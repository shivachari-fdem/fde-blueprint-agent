import json
import time
import uuid
import difflib

def _generate_metadata(tool_name: str, start_time: float) -> dict:
    """Generates enterprise-grade observability metadata for tracing."""
    return {
        "trace_id": f"fde-trace-{uuid.uuid4().hex[:8]}",
        "tool_name": tool_name,
        "execution_time_ms": round((time.time() - start_time) * 1000, 2),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

def lookup_gcp_service(args_json: str) -> str:
    """
    Mock database lookup for GCP services (Low Stakes) with fuzzy matching.
    
    Args:
        args_json (str): A JSON string. Expected properties:
            - service_name (str): The name of the GCP service to look up.
            
    Returns:
        str: JSON string containing the service description, status, and telemetry metadata.
    """
    start_time = time.time()
    try:
        print(f"\n[Tool Execution] Running lookup_gcp_service with args: {args_json}")
        args = json.loads(args_json)
        original_query = args.get("service_name", "").lower().strip()

        mock_db = {
            "compute engine": "Google Compute Engine (GCE) provides highly customizable virtual machines.",
            "cloud storage": "Google Cloud Storage (GCS) is a highly durable, enterprise-grade object storage service.",
            "cloud run": "Cloud Run is a managed compute platform that lets you run containers directly on Google's scalable infrastructure.",
            "cloud spanner": "Cloud Spanner is a fully managed, mission-critical, relational database service that offers transactional consistency at global scale."
        }

        # INNOVATION: Fuzzy matching to auto-correct LLM typos or slight hallucinations
        db_keys = list(mock_db.keys())
        matches = difflib.get_close_matches(original_query, db_keys, n=1, cutoff=0.6)

        response_payload = {}
        if matches:
            matched_key = matches[0]
            response_payload = {
                "service": matched_key,
                "original_query": original_query,
                "internal_description": mock_db[matched_key],
                "status": "found_in_internal_db" if matched_key == original_query else "fuzzy_matched_auto_corrected"
            }
        else:
            response_payload = {
                "service": original_query,
                "internal_description": "Service not found in internal FDE database. Proceed using general foundational knowledge.",
                "status": "not_found"
            }

        response_payload["_meta"] = _generate_metadata("lookup_gcp_service", start_time)
        return json.dumps(response_payload)

    except Exception as e:
        return json.dumps({
            "error": f"Tool execution failed: {str(e)}",
            "instruction": "Please review the JSON string format and ensure 'service_name' is provided.",
            "_meta": _generate_metadata("lookup_gcp_service", start_time)
        })

def get_cost_estimate(args_json: str) -> str:
    """
    Mock cost estimator (High Stakes - Requires Approval) with self-healing parameters.
    
    Args:
        args_json (str): A JSON string. Expected properties:
            - service_name (str): The name of the Google Cloud service.
            - usage_tier (str): The expected usage tier ("Low", "Medium", or "High").
            
    Returns:
        str: JSON string containing the estimated cost, currency, and telemetry metadata.
    """
    start_time = time.time()
    try:
        print(f"\n[Tool Execution] Running get_cost_estimate with args: {args_json}")
        args = json.loads(args_json)
        
        if "service_name" not in args or "usage_tier" not in args:
            raise ValueError("Missing required parameter: 'service_name' and/or 'usage_tier' are missing.")
            
        service_name = args.get("service_name")
        # INNOVATION: Capitalize automatically to handle minor case-sensitivity mistakes from the LLM
        usage_tier = str(args.get("usage_tier", "")).capitalize() 

        tier_multipliers = {"Low": 50, "Medium": 500, "High": 5000}
        
        if usage_tier not in tier_multipliers:
            # INNOVATION: Feed the exact allowed keys back to the LLM for immediate self-correction
            valid_options = ", ".join(tier_multipliers.keys())
            raise ValueError(f"Invalid usage_tier '{usage_tier}'. Valid options are strictly: [{valid_options}]")
            
        response_payload = {
            "service": service_name,
            "usage_tier": usage_tier,
            "estimated_monthly_cost_usd": tier_multipliers.get(usage_tier, 0),
            "currency": "USD",
            "notes": "Internal FDE estimate. Final pricing may vary based on region."
        }
        
        response_payload["_meta"] = _generate_metadata("get_cost_estimate", start_time)
        return json.dumps(response_payload)

    except Exception as e:
        return json.dumps({
            "error": f"Tool execution failed: {str(e)}",
            "instruction": "Please correct the JSON parameters based on the error message and try invoking the tool again.",
            "_meta": _generate_metadata("get_cost_estimate", start_time)
        })
