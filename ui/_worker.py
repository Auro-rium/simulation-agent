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
            payload = event.get("payload")
            timestamp = event.get("timestamp")
            
            # Format time
            time_str = ""
            if timestamp:
                # keep HH:MM:SS
                time_str = timestamp.split("T")[-1].split(".")[0]
            
            if e_type == "status":
                text = event.get("text", "")
                self.q.put({"type": "turn", "payload": f"[{time_str}] [SYSTEM] {text}"})
                
            elif e_type == "plan":
                steps = payload.get("steps", [])
                self.q.put({"type": "turn", "payload": f"[{time_str}] [PLANNER] Generated {len(steps)} step plan."})
                for s in steps:
                     self.q.put({"type": "turn", "payload": f"  > {s.get('task')}"})
                     
            elif e_type == "specialist_done":
                agent = event.get("agent")
                meta = payload.get("meta", {})
                lat = meta.get("latency_ms", 0)
                
                # Extract analysis text
                output = payload.get("output", {})
                # Try to get nested analysis string or just dump
                if isinstance(output, dict):
                     # Find likely keys
                     val = output.get("security_analysis") or output.get("technology_analysis") or output.get("economics_analysis") or str(output)
                else:
                     val = str(output)
                
                # Update Card
                self.q.put({"type": "card_update", "agent": agent.lower(), "content": str(val)})
                self.q.put({"type": "turn", "payload": f"[{time_str}] [{agent}] Analysis complete ({lat:.0f}ms)."})

            elif e_type == "constraint":
                is_safe = payload.get("is_safe")
                self.q.put({"type": "turn", "payload": f"[{time_str}] [CONSTRAINT] Safety Check: {'PASSED' if is_safe else 'FAILED'}"})
                
            elif e_type == "turn":
                # Simulation turn
                turn = payload
                actor = turn.get("actor")
                action = turn.get("action")
                self.q.put({"type": "turn", "payload": f"[{time_str}] [SIM] Turn {event.get('index')}: {actor}"})
                self.q.put({"type": "turn", "payload": f"  Action: {action}"})
                self.q.put({"type": "timeline_update", "turn": turn})
                
            elif e_type == "done":
                 self.q.put({"type": "done", "payload": payload})

        try:
            self.q.put({"type": "turn", "payload": "[SYSTEM] Initializing secure channel..."})
            
            # Run the Async Manager in this thread with a new loop
            # We use a wrapper to handle the coroutine execution
            async def runner():
                 return await manager_run(
                     self.request, 
                     self.context, 
                     progress_callback=progress_callback
                 )
            
            result = asyncio.run(runner())
            
            # "done" event is usually emitted by manager_run, but let's ensure we handle the result 
            # if the loop finished but done wasn't explicitly caught or if we need to pass the full dict back
            # The manager_run should have emitted 'done' if we implemented it there? 
            # Checked manager_run: it emits 'done' at the end.
            
            # If for some reason we didn't get done (e.g. exception swallowed), we ensure it here
            # But normally manager_run returns the dict
            
        except InterruptedError:
            self.q.put({"type": "turn", "payload": "[SYSTEM] ABORTED BY USER."})
        except Exception as e:
            import traceback
            self.q.put({"type": "error", "payload": str(e), "trace": traceback.format_exc()})
