import uvicorn
import os
import sys
from dotenv import load_dotenv

# Load env vars first
load_dotenv()

# Ensure project root is in python path
sys.path.append(os.getcwd())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Multi-Agent Server on port {port}...")
    uvicorn.run("orchestration.api:app", host="0.0.0.0", port=port, reload=True)
