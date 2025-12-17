import os
from dotenv import load_dotenv, find_dotenv

print(f"CWD: {os.getcwd()}")
env_path = find_dotenv()
print(f"Found .env at: {env_path}")

loaded = load_dotenv()
print(f"load_dotenv returned: {loaded}")

key = os.environ.get("GROQ_API_KEY")
print(f"GROQ_API_KEY: {key[:5] if key else 'None'}...")
