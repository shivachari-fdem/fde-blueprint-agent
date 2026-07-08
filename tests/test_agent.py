import pytest
import json
from tools import lookup_gcp_service, get_cost_estimate

def test_lookup_gcp_service_exact_match():
    # Test strict matching
    response_json = lookup_gcp_service(json.dumps({"service_name": "compute engine"}))
    res = json.loads(response_json)
    assert res["status"] == "found_in_internal_db"
    assert "Google Compute Engine" in res["internal_description"]

def test_lookup_gcp_service_fuzzy_match():
    # Test fuzzy matching auto-correction
    response_json = lookup_gcp_service(json.dumps({"service_name": "comput engnie"}))
    res = json.loads(response_json)
    assert res["status"] == "fuzzy_matched_auto_corrected"
    assert res["service"] == "compute engine"

def test_get_cost_estimate_validation():
    # Test high-stakes input self-healing validator
    response_json = get_cost_estimate(json.dumps({"service_name": "spanner", "usage_tier": "INVALID"}))
    res = json.loads(response_json)
    assert "error" in res
    assert "Invalid usage_tier 'Invalid'." in res["error"]
