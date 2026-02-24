import sys
import os
import asyncio
import hashlib

# ====== ضبط المسارات (قبل استيراد brain و agents) ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from brain.logger_setup import get_logger
from agents.hunter_agent import HunterAgent
from agents.filter_agent import FilterAgent
from agents.sentiment_agent import SentimentAgent
from agents.baseagent import BaseAgent

# ====== إعداد Logger مركزي ======
logger = get_logger("MarketIntel-Orchestrator")

# ====== Hash للتحقق من سلامة الملفات ======
def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

# ملفات أساسية مع الـ Hash الأصلي (يُحدَّث عند تغيير الملفات المعتمدة)
FILES_HASHES = {
    "agents/baseagent.py": "f086273bfa5aa2171d38030861b2fd954b89846147ef8f04dc477e3ee0e18cc9",
}

# ====== تحقق من سلامة الملفات ======
for file, original_hash in FILES_HASHES.items():
    path = os.path.join(BASE_DIR, file)
    if not os.path.exists(path):
        raise RuntimeError("ملف اساسي مفقود: %s" % file)
    if file_hash(path) != original_hash:
        raise RuntimeError("تم تعديل الملف %s بدون إذن! توقف التنفيذ." % file)

# ====== تهيئة الوكلاء ======
hunter = HunterAgent(name="HunterAgent", logger=logger)
filter_agent = FilterAgent(name="FilterAgent", logger=logger)
sentiment_agent = SentimentAgent(name="SentimentAgent", logger=logger)

# ====== Pipeline محمي ======
async def run_pipeline(initial_input=None):
    logger.info("بدء تنفيذ الـ Pipeline المحمي")

    payload = initial_input if initial_input is not None else {"query": "market intelligence"}

    try:
        hunter_data = await asyncio.to_thread(hunter.run, payload)
    except Exception as e:
        logger.error("Pipeline فشل: %s", e)
        return None

    try:
        filter_data = await asyncio.to_thread(filter_agent.run, hunter_data)
    except Exception as e:
        logger.error("Pipeline فشل: %s", e)
        return None

    try:
        sentiment_data = await asyncio.to_thread(sentiment_agent.run, filter_data)
    except Exception as e:
        logger.error("Pipeline فشل: %s", e)
        return None

    logger.info("نتائج Pipeline النهائية: %s", sentiment_data)
    return sentiment_data

# ====== تشغيل Async Main Loop ======
if __name__ == "__main__":
    asyncio.run(run_pipeline())
