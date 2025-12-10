import asyncio
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from orchestration.manager import async_manager

router = APIRouter()

@router.get("/stream/{run_id}")
async def message_stream(run_id: str):
    """
    Simulates streaming events for a specific run.
    Real implementation would hook into a pub/sub or database of events.
    """
    async def event_generator():
        # Echo example
        yield {"event": "connect", "data": "connected"}
        await asyncio.sleep(1)
        yield {"event": "progress", "data": "Planning..."}
        # In a real system, manager would push events to a Redis queue 
        # and this endpoint would pop them.
    
    return EventSourceResponse(event_generator())
