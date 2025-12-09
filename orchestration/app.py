from agents.manager_agent import ManagerAgent
import logging

# In a real ADK app, we might decorate this or inherit from 'AdkApp'.
# For this Python generic implementation which can run on any container,
# we wrap the ManagerAgent.

logger = logging.getLogger("adk_app")

class MultiAgentApp:
    def __init__(self):
        self.manager = ManagerAgent()

    def handle_request(self, user_request: str, context: dict = None) -> dict:
        if context is None:
            context = {}
        logger.info(f"Received request: {user_request}")
        return self.manager.run({"request": user_request, "context": context})

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
