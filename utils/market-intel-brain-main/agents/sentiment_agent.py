import json
import textblob
# استيراد الأدوات اللازمة بدون كلمة brain
try:
    from agents.baseagent import AgentBase
    from brain.logger_setup import setup_logger
except ImportError:
    from .baseagent import AgentBase
    from brain.logger_setup import setup_logger

class SentimentAgent(AgentBase):
    def __init__(self, logger=None):
        logger = logger or setup_logger("SentimentAgent")
        super().__init__("SentimentAgent", logger)

    def run(self, text):
        """نقطة دخول الوكيل المتوافقة مع الـ Pipeline الرئيسي."""
        try:
            self.logger.info("SentimentAgent started analysis...")
            blob = textblob.TextBlob(text)
            polarity = blob.sentiment.polarity

            if polarity > 0:
                label = "positive"
            elif polarity < 0:
                label = "negative"
            else:
                label = "neutral"

            result = {
                "agent": "SentimentAgent",
                "polarity": round(polarity, 2),
                "label": label
            }
            
            self.logger.info(f"SentimentAgent finished: {result}")
            return result

        except Exception as e:
            self.logger.error(f"SentimentAgent crashed: {e}")
            return {"error": str(e), "label": "unknown"}

# Standalone test
if __name__ == "__main__":
    agent = SentimentAgent()
    test_text = "Bitcoin is surging strongly today!"
    print(json.dumps(agent.run(test_text), indent=2))
