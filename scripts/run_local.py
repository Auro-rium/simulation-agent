import sys
import os
import yaml
import json
from dotenv import load_dotenv

# Load env vars first
load_dotenv()

# Ensure project root is in python path
sys.path.append(os.getcwd())

from orchestration.app import app_instance

def main():
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        print("Warning: GOOGLE_CLOUD_PROJECT env var not set. Vertex AI calls may fail.")

    print("--- Diplomatic Simulation Agent (CLI) ---")
    
    # 1. User Request
    default_req = "Analyze a potential trade agreement negotiation between these actors."
    user_request = input(f"\nEnter Analysis Request (default: '{default_req}'):\n") or default_req

    # 2. Risk Tolerance
    print("\nSelect Risk Tolerance for Actor A:")
    print("1. Low")
    print("2. Moderate (default)")
    print("3. High")
    risk_choice = input("Choice (1-3): ")
    risk_map = {"1": "Low", "2": "Moderate", "3": "High"}
    risk_tolerance = risk_map.get(risk_choice, "Moderate")

    # 3. Global Conditions
    default_global = "Global energy crisis, high inflation"
    global_cond = input(f"\nEnter Global Condition (default: '{default_global}'):\n") or default_global

    print("\nInitializing Scenario...")
    
    # Inline default for testing without config files, but updated with user inputs
    scenario = {
        "context": {
            "global_condition": global_cond,
            "risk_tolerance": risk_tolerance
        },
        "actors": {
            "A": "Developing Nation with resource wealth",
            "B": "Developed Nation with technology",
            "C": "International Regulator"
        },
        "strategies": {
            "Initial_Proposal": "Propose a joint venture with shared IP.",
            "Fallback_Plan": "Seek alternative funding if rejected."
        },
        "max_turns": 3
    }
    
    print(f"Running Agent System for: {user_request}")
    print("-" * 40)
    
    try:
        result = app_instance.handle_request(user_request, scenario)
        
        print("\n\n=== FINAL OUTPUT ===\n")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
