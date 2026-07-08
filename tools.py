import json
import time
import uuid
import difflib
from opentelemetry import trace

tracer = trace.get_tracer("fde_tools")

def _generate_metadata(tool_name: str, start_time: float) -> dict:
    """Generates enterprise-grade observability metadata using OpenTelemetry."""
    span = trace.get_current_span()
    trace_id = format(span.get_span_context().trace_id, "032x") if span.is_recording() else f"trace-{uuid.uuid4().hex[:8]}"
    return {
        "trace_id": trace_id,
        "tool_name": tool_name,
        "execution_time_ms": round((time.time() - start_time) * 1000, 2),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

def lookup_gcp_service(args_json: str) -> str:
    start_time = time.time()
    with tracer.start_as_current_span("lookup_gcp_service") as span:
        span.set_attribute("tool.name", "lookup_gcp_service")
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
            span.set_attribute("tool.status", "success")
            return json.dumps(response_payload)

        except Exception as e:
            span.record_exception(e)
            span.set_attribute("tool.status", "error")
            return json.dumps({
                "error": f"Tool execution failed: {str(e)}",
                "instruction": "Please review the JSON string format and ensure 'service_name' is provided.",
                "_meta": _generate_metadata("lookup_gcp_service", start_time)
            })

def get_cost_estimate(args_json: str) -> str:
    start_time = time.time()
    with tracer.start_as_current_span("get_cost_estimate") as span:
        span.set_attribute("tool.name", "get_cost_estimate")
        try:
            print(f"\n[Tool Execution] Running get_cost_estimate with args: {args_json}")
            args = json.loads(args_json)
            
            if "service_name" not in args or "usage_tier" not in args:
                raise ValueError("Missing required parameter: 'service_name' and/or 'usage_tier' are missing.")
                
            service_name = args.get("service_name")
            usage_tier = str(args.get("usage_tier", "")).capitalize() 

            tier_multipliers = {"Low": 50, "Medium": 500, "High": 5000}
            
            if usage_tier not in tier_multipliers:
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
            span.set_attribute("tool.status", "success")
            return json.dumps(response_payload)

        except Exception as e:
            span.record_exception(e)
            span.set_attribute("tool.status", "error")
            return json.dumps({
                "error": f"Tool execution failed: {str(e)}",
                "instruction": "Please correct the JSON parameters based on the error message and try invoking the tool again.",
                "_meta": _generate_metadata("get_cost_estimate", start_time)
            })
