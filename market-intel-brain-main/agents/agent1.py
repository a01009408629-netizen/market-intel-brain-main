from .baseagent import BaseAgent

class Agent1(BaseAgent):
    def __init__(self, logger=None):
        super().__init__("Agent 1", logger)

    def run(self, text):
        # أي معالجة أولية أو تحليل
        return text.upper()
