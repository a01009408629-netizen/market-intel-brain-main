import re
import json
# تصحيح الاستدعاءات: حذف كلمة brain. لأن المجلدات في المسار الرئيسي
try:
    from agents.baseagent import AgentBase
    from brain.logger_setup import setup_logger
except ImportError:
    from .baseagent import AgentBase
    from brain.logger_setup import setup_logger

class FilterAgent(AgentBase):
    def __init__(self, logger=None):
        logger = logger or setup_logger("FilterAgent")
        super().__init__("FilterAgent", logger)

        # Patterns قابلة للتوسّع
        self.noise_patterns = [
            r"http\S+",                 # URLs
            r"\bBUY NOW\b",
            r"\bCLICK HERE\b",
            r"\bFREE\b",
            r"\b[A-Z]{5,}\b",           # Spam uppercase
            r"!!!!+",                   # Excessive punctuation
            r"[^\w\s.,?!-:؛،]+"         # Emojis and symbols
        ]

    def clean_text(self, text):
        """إزالة الروابط، الرموز، الإيموجيز، وتوحيد المسافات."""
        try:
            cleaned = text
            cleaned = re.sub(r"http\S+", "", cleaned)
            cleaned = re.sub(r"[^\w\s.,?!-:؛،]", "", cleaned)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            return cleaned
        except Exception as e:
            self.logger.error(f"clean_text failed: {e}")
            return text

    def calculate_noise_score(self, text):
        """حساب مدى كون النص ضوضائي أو Spam."""
        score = 0
        for pattern in self.noise_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 1
        return score

    def filter_logic(self, text):
        cleaned = self.clean_text(text)
        noise_score = self.calculate_noise_score(text) # الفحص يتم على النص الأصلي لكشف الروابط والسبام

        return {
            "original_text": text,
            "cleaned_text": cleaned,
            "noise_score": noise_score,
            "is_noise": noise_score >= 2,
        }

    def run(self, text):
        try:
            self.logger.info("FilterAgent started filtering...")
            result = self.filter_logic(text)
            self.logger.info(f"FilterAgent finished: {result}")
            return result
        except Exception as e:
            self.logger.error(f"FilterAgent crashed: {e}")
            return {"error": str(e)}

# Standalone test
if __name__ == "__main__":
    agent = FilterAgent()
    test = "BUY NOW!!!! Visit http://spam.com 😀😀 CLICK HERE!"
    print(json.dumps(agent.run(test), indent=2))
