from agents.baseagent import BaseAgent


class HunterAgent(BaseAgent):
    _protected = True  # حماية ضد تعديل BaseAgent

    def run(self, data=None) -> dict:
        self._check_integrity()  # تحقق داخلي من BaseAgent
        self.log("جاري استخراج البيانات الأولية...")
        # مثال بيانات أولية
        extracted_data = {
            "original_text": "Bitcoin price is surging to the moon! 🚀🚀🚀"
        }
        return extracted_data
