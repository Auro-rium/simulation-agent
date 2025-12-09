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

def load_config(path: str):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def main():
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        print("Warning: GOOGLE_CLOUD_PROJECT env var not set. Vertex AI calls may fail.")

    print("Loading scenario...")
    config_path = "configs/example_scenario.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    scenario = load_config(config_path)
    
    user_request = "Analyze a potential trade agreement negotiation between these actors."
    
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
