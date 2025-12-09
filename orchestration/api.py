from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from orchestration.app import app_instance

app = FastAPI(title="Multi-Agent Simulation API")

class AnalyzeRequest(BaseModel):
    request: str
    context: Optional[Dict[str, Any]] = {}

@app.post("/analyze")
async def analyze_endpoint(payload: AnalyzeRequest):
    try:
        result = app_instance.handle_request(payload.request, payload.context)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok"}
