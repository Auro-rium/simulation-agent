from typing import Any, Dict
import logging
from llm.llm_client import LLMClient

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class BaseAgent:
    """Base class for all agents in the system."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        self.llm_client = LLMClient()

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Main execution method to be implemented by subclasses."""
        raise NotImplementedError("Agents must implement the run method")

    def log(self, message: str):
        self.logger.info(message)
