class AnalyzerAgent:
    def __init__(self):
        pass

    def combine(self, raw_data, filtered_data, sentiment_data):
        final_report = []

        for url in raw_data.keys():
            entry = {
                "source": url,
                "raw_text": raw_data.get(url, ""),
                "filtered_text": filtered_data.get(url, ""),
                "sentiment": sentiment_data.get(url, {})
            }
            final_report.append(entry)

        return final_report

    def analyze(self, text):
        # تحليل مبدئي بسيط عشان brain.py يشتغل بدون errors
        return {"analysis": text}


if __name__ == "__main__":
    agent = AnalyzerAgent()
    sample_raw = {"url1": "Bitcoin rises again today"}
    sample_filtered = {"url1": "Bitcoin rises"}
    sample_sentiment = {"url1": {"polarity": 0.7, "label": "positive"}}

    print(agent.combine(sample_raw, sample_filtered, sample_sentiment))
    print(agent.analyze("Test input"))
