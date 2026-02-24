import importlib
import os
import sys
from logger_setup import setup_logger

class Brain:

    def __init__(self, agents_folder="agents"):
        self.logger = setup_logger()
        self.logger.info("Brain initialized")

        self.agents = []
        self.agents_folder = agents_folder
        self.load_agents()

    def load_agents(self):
        """Load all agent modules from the agents folder automatically"""
        folder_path = os.path.join(os.path.dirname(__file__), self.agents_folder)
        if not os.path.exists(folder_path):
            self.logger.error(f"Agents folder '{folder_path}' not found!")
            return

        for filename in os.listdir(folder_path):
            if filename.endswith(".py") and filename not in ["__init__.py", "base_agent.py"]:
                module_name = filename[:-3]  # remove .py
                try:
                    module = importlib.import_module(f"{self.agents_folder}.{module_name}")
                    # Find any class that inherits BaseAgent
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type):
                            bases = [base.__name__ for base in attr.__bases__]
                            if "BaseAgent" in bases:
                                self.logger.info(f"Loading agent: {attr_name}")
                                agent_instance = attr(logger=self.logger)
                                self.agents.append(agent_instance)
                except Exception as e:
                    self.logger.error(f"Failed to load module {module_name}: {e}")

    def validate_input(self, text):
        if not isinstance(text, str):
            self.logger.error("Invalid input type (must be string)")
            return False
        if text.strip() == "":
            self.logger.error("Empty input text")
            return False
        return True

    def run(self, text):
        if not self.validate_input(text):
            return []

        results = []

        for agent in self.agents:
            self.logger.info(f"Executing {agent.name}")
            output = agent.safe_run(text)
            self.logger.info(f"{agent.name} finished")

            results.append({
                "agent": agent.name,
                "input": text,
                "output": output
            })

        return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("No input text provided")
        sys.exit(1)

    input_text = " ".join(sys.argv[1:])
    brain = Brain()
    result = brain.run(input_text)
    print(result)
