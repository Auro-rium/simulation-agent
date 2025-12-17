import threading
import queue
import time
import json
from typing import Dict
from orchestration.app import app_instance

class Worker(threading.Thread):
    def __init__(self, q: queue.Queue, request: str, context: Dict, control: Dict):
        super().__init__(daemon=True)
        self.q = q
        self.request = request
        self.context = context
        self.control = control  # e.g., {'paused': False, 'stop': False}

    def run(self):
        import asyncio
        from orchestration.manager_run import manager_run
        
        # Callback to bridge manager events to queue
        def progress_callback(event: Dict):
             if self.control.get("stop", False):
                 raise InterruptedError("Stopped by user")
                 
             e_type = event.get("type")
             # Pass through the raw event structure to app.py
             # app.py handles 'plan', 'specialist_decision', 'composite', 'constraint', etc.
             
             # Map 'status' to generic logging if needed, or pass through
             if e_type == "status":
                 self.q.put({"type": "status", "payload": event.get("text")})
                 
             elif e_type == "plan":
                 self.q.put({"type": "plan", "payload": event.get("payload")})
                 
             elif e_type == "specialist_decision":
                 self.q.put({
                     "type": "specialist_decision", 
                     "agent": event.get("agent"), 
                     "payload": event.get("payload")
                 })
                 
             elif e_type == "composite":
                 self.q.put({"type": "composite", "payload": event.get("payload")})
                 
             elif e_type == "constraint":
                 self.q.put({"type": "constraint", "payload": event.get("payload")})
                 
             elif e_type == "judgment":
                 self.q.put({"type": "judgment", "payload": event.get("payload")})
                 
             elif e_type == "simulation":
                 self.q.put({"type": "simulation", "payload": event.get("payload")})
                 
             elif e_type == "done":
                 self.q.put({"type": "done", "payload": event.get("payload")})

        try:
            # Run the Async Manager
            async def runner():
                 return await manager_run(
                     self.request, 
                     self.context, 
                     progress_callback=progress_callback
                 )
            
            asyncio.run(runner())
            
        except InterruptedError:
            self.q.put({"type": "status", "payload": "ABORTED BY COMMAND."})
        except Exception as e:
            import traceback
            # Log full error
            print(traceback.format_exc())
            self.q.put({"type": "error", "payload": str(e)})
