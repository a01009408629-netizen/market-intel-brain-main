from agents.baseagent import BaseAgent


class FilterAgent(BaseAgent):
    """
    الوكيل الثاني في السلسلة.
    مسؤوليته تنظيف وتصنيف البيانات القادمة من HunterAgent.
    """

    def run(self, data=None) -> dict:
        self.log("بدء فلترة البيانات")

        if data is None or "clean_input" not in data:
            return {
                "status": "error",
                "message": "FilterAgent: لا توجد بيانات صالحة للفلترة."
            }

        # مثال تنظيف البيانات: إزالة فراغات إضافية وتحويل النص إلى lowercase
        cleaned_data = str(data["clean_input"]).strip().lower()

        self.log("اكتملت فلترة البيانات")
        return {
            "status": "success",
            "filtered_data": cleaned_data
        }
