from agents.registry.agent_registry import AgentRegistry
from messaging.message_bus import MessageBus

# -----------------------------
# إنشاء Registry و MessageBus
# -----------------------------
registry = AgentRegistry()
bus = MessageBus()

# -----------------------------
# إنشاء Agents وهميين للاختبار
# -----------------------------
class DummyAgent:
    def __init__(self, name):
        self.name = name
    def safe_run(self, message):
        print(f"[{self.name}] received: {message}")
        return f"{self.name} processed the message"

# تسجيل الـ Dummy Agents
registry.register("EconomicAgent", DummyAgent("EconomicAgent"))
registry.register("GeoAgent", DummyAgent("GeoAgent"))
registry.register("SentimentAgent", DummyAgent("SentimentAgent"))

# -----------------------------
# ربطهم بالـ MessageBus
# -----------------------------
registry.subscribe_all(bus)

# -----------------------------
# تشغيل الـ MessageBus
# -----------------------------
bus.start()

# -----------------------------
# إرسال Broadcast تجريبي لكل الـ Agents
# -----------------------------
bus.broadcast("ابدأ تحليل")

# -----------------------------
# مثال إرسال رسالة لواحد Agent فقط
# -----------------------------
bus.send("GeoAgent", "رسالة مباشرة لـ GeoAgent")
