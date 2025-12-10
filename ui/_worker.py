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
        try:
            self.q.put({"type": "progress", "value": 10, "text": "Initializing Agents..."})
            time.sleep(0.5)

            # 1. PLANNING PHASE
            self.q.put({"type": "progress", "value": 20, "text": "Manager: formulating plan..."})
            
            # Since app_instance is synchronous, we call it and wait.
            # Ideally, we'd hook into logs or callbacks, but for this refactor we simulate progress
            # just before the big call, and then chunk the result.
            
            # We can use a timer thread to fake "thinking" progress while we wait
            stop_progress = threading.Event()
            def fake_progress():
                p = 20
                while not stop_progress.is_set() and p < 80:
                    time.sleep(1.0)
                    p += 2
                    self.q.put({"type": "progress", "value": p, "text": "Agents analyzing..."})
            
            prog_thread = threading.Thread(target=fake_progress, daemon=True)
            prog_thread.start()

            # --- THE BIG CALL ---
            result = app_instance.handle_request(self.request, self.context)
            # --------------------
            
            stop_progress.set()
            prog_thread.join()
            
            if "manager_report" not in result:
                raise ValueError("Invalid result from backend")

            # 2. EMIT EVENTS "REPLAY" STYLE
            # Unpack the result to make it feel like a stream
            
            # Emit Plan
            plan_steps = result.get("plan_summary", [])
            for step in plan_steps:
                self.q.put({"type": "turn", "payload": f"[MANAGER] Planned step: {step}", "index": 0})
                time.sleep(0.3)
            
            # Emit Specialist Findings
            findings = result.get("specialist_findings", {})
            for agent, analysis in findings.items():
                prefix = f"[{agent.upper()}]"
                # Split analysis into chunks for readability
                lines = analysis.split('\n')
                summary = lines[0] if lines else "Analysis complete."
                self.q.put({"type": "turn", "payload": f"{prefix} {summary}", "index": 0})
                # Send full card update
                self.q.put({"type": "card_update", "agent": agent, "content": analysis})
                time.sleep(0.5)

            # Emit Constraints
            constraints = result.get("constraints", {})
            self.q.put({"type": "turn", "payload": f"[CONSTRAINT] Sanity Check: {constraints.get('warnings', 'None')}", "index": 0})
            time.sleep(0.5)

            # Emit Simulation Turns
            sim_result = result.get("simulation_result", {})
            history = sim_result.get("simulation_history", []) if isinstance(sim_result, dict) else []
            
            if not history and isinstance(sim_result, str):
                 self.q.put({"type": "turn", "payload": f"[SIMULATION] {sim_result}", "index": 0})

            for idx, turn in enumerate(history):
                # Check Pause
                while self.control.get("paused", False):
                    time.sleep(0.2)
                    if self.control.get("stop", False):
                         return

                actor = turn.get("actor", "System")
                action = turn.get("action", "No action")
                self.q.put({"type": "turn", "payload": f"Turn {idx+1}: {actor} -> {action}", "index": idx})
                self.q.put({"type": "timeline_update", "turn": turn})
                time.sleep(0.8) # Artificial delay for readability

            # Finalize
            self.q.put({"type": "progress", "value": 100, "text": "Synthesis Complete."})
            self.q.put({"type": "done", "payload": result})

        except Exception as e:
            import traceback
            self.q.put({"type": "error", "payload": str(e), "trace": traceback.format_exc()})
