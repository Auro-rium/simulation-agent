import asyncio
import logging
import json
from typing import Dict, Any, List

from orchestration.manager_run import manager_run
from core.schemas import FinalReport

logger = logging.getLogger("manager_v2")

class AsyncManager:
    """
    Backward compatible wrapper that now runs the optimized manager_run loop.
    """
    def __init__(self):
        # We no longer explicitly init agents here as manager_run handles them with llm_client
        pass

    async def run(self, request: str, context: Dict[str, Any]) -> FinalReport:
        # manager_run returns Dict, we wrap it back to FinalReport for compatibility
        result_dict = await manager_run(request, context)
        return FinalReport(**result_dict)

# Global Async Instance
async_manager = AsyncManager()

# Synchronous Wrapper for Backwards Compatibility with App.py
def run_sync_wrapper(request, context):
    return asyncio.run(async_manager.run(request, context)).model_dump()
