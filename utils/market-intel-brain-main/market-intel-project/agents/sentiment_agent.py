from agents.baseagent import BaseAgent


class SentimentAgent(BaseAgent):
    """
    الوكيل الثالث في السلسلة.
    مسؤوليته تحليل المشاعر (Sentiment) للبيانات النظيفة القادمة من FilterAgent.
    """

    def run(self, data=None) -> dict:
        self.log("بدء تحليل المشاعر")

        if data is None or "filtered_data" not in data:
            return {
                "status": "error",
                "message": "SentimentAgent: لا توجد بيانات صالحة للتحليل."
            }

        # مثال: تحليل بسيط للمشاعر (إيجابي/سلبي) بناءً على كلمات مفتاحية
        text = str(data["filtered_data"])
        sentiment = "neutral"
        if any(word in text for word in ["good", "great", "profit", "up"]):
            sentiment = "positive"
        elif any(word in text for word in ["bad", "loss", "down", "fall"]):
            sentiment = "negative"

        self.log(f"انتهى تحليل المشاعر: {sentiment}")
        return {
            "status": "success",
            "sentiment": sentiment
        }
