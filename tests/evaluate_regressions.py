import json
import asyncio
from agent import FDEOrchestrator

async def run_regression_suite():
    print("🚀 Starting FDE Agent Golden Dataset Regression Evaluation...")
    with open("tests/golden_dataset.json", "r") as f:
        dataset = json.load(f)
        
    # Initialize the orchestrator for testing
    orchestrator = FDEOrchestrator(project_id="test-project", session_id="eval_session")
    passed = 0
    total = len(dataset)
    
    print("-" * 50)
    for case in dataset:
        original = case["input"]
        
        # Test routing exactly as it behaves in production
        intent = await orchestrator._route_intent(original)
        
        if intent == case["expected_intent"]:
            passed += 1
            print(f"[✅ PASS] Input: '{original[:30]}...' -> Intent: {intent}")
        else:
            print(f"[❌ FAIL] Input: '{original[:30]}...' -> Expected: {case['expected_intent']}, Got: {intent}")
            
    print("-" * 50)
    print(f"📊 Regression Suite Complete. Accuracy Score: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed < total:
        print("⚠️ Warning: Regressions detected against golden dataset!")
        exit(1)
    else:
        print("🏆 All golden tests passed! Output is safe for production.")

if __name__ == "__main__":
    asyncio.run(run_regression_suite())
