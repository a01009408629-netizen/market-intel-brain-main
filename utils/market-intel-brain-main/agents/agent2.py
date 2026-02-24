from .base_agent import BaseAgent

class Agent2(BaseAgent):
    def __init__(self, logger=None):
        super().__init__("Agent 2", logger)

    def run(self, text):
        # أي معالجة ثانية أو تحليل مختلف
        return text[::-1]
