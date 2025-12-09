from agents.manager_agent import ManagerAgent
import logging

# In a real ADK app, we might decorate this or inherit from 'AdkApp'.
# For this Python generic implementation which can run on any container,
# we wrap the ManagerAgent.

logger = logging.getLogger("adk_app")

class MultiAgentApp:
    def __init__(self):
        self._manager = None
        self._init_error = None
        
    @property
    def manager(self):
        if self._manager is None:
            try:
                self._manager = ManagerAgent()
            except Exception as e:
                self._init_error = str(e)
                logger.error(f"Failed to initialize ManagerAgent: {e}")
                # We return None or raise, but handle_request needs to deal with it
                raise e
        return self._manager

    def handle_request(self, user_request: str, context: dict = None) -> dict:
        try:
            # Trigger lazy load
            mgr = self.manager
        except Exception as e:
            # Return a structured error response that the UI can render
            return {
                "manager_report": f"SYSTEM ERROR: Agent Initialization Failed.\n\nReason: {e}\n\nPlease check your Environment Variables (GOOGLE_CLOUD_PROJECT, VERTEX_AI_LOCATION) in Replit Secrets.",
                "constraints": {"is_safe": False, "warnings": ["System Configuration Error"]},
                "simulation_result": "Simulation Aborted."
            }

        if context is None:
            context = {}
        logger.info(f"Received request: {user_request}")
        return mgr.run({"request": user_request, "context": context})

# Global instance
app_instance = MultiAgentApp()

def entry_point(request_body: dict):
    """
    Standard entry point for generic runners.
    Expects {'request': '...', 'context': {...}}
    """
    req = request_body.get("request")
    ctx = request_body.get("context", {})
    return app_instance.handle_request(req, ctx)
