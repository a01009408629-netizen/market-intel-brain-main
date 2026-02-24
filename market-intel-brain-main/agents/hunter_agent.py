import json
# تصحيح الاستدعاءات وحذف كلمة brain.
try:
    from agents.baseagent import AgentBase
    from brain.logger_setup import setup_logger
except ImportError:
    from .baseagent import AgentBase
    from brain.logger_setup import setup_logger

class HunterAgent(AgentBase):
    def __init__(self, logger=None):
        logger = logger or setup_logger("HunterAgent")
        super().__init__("HunterAgent", logger)

    def hunt_keywords(self, text):
        """البحث عن كلمات مهمة داخل النص."""
        keywords = ["market", "price", "stock", "bitcoin", "analysis"]
        found = []

        for word in keywords:
            if word.lower() in text.lower():
                found.append(word)

        return found

    def run(self, text):
        """نقطة دخول الوكيل."""
        try:
            self.logger.info("HunterAgent started...")
            found = self.hunt_keywords(text)

            result = {
                "agent": "HunterAgent",
                "found_keywords": found,
                "count": len(found)
            }

            self.logger.info(f"HunterAgent finished: {result}")
            return result

        except Exception as e:
            self.logger.error(f"HunterAgent crashed: {e}")
            return {"error": str(e)}

# Standalone test
if __name__ == "__main__":
    agent = HunterAgent()
    test = "The market price of bitcoin is rising fast."
    print(json.dumps(agent.run(test), indent=2))
