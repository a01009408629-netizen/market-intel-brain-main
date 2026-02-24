class AgentRegistry:
    def __init__(self):
        # هنا بيتسجّل كل Agent في النظام
        self.agents = {}

    def register(self, agent_name, agent_instance):
        """
        تسجيل Agent جديد في النظام.
        """
        if agent_name in self.agents:
            raise ValueError(f"Agent '{agent_name}' already registered.")

        self.agents[agent_name] = agent_instance

    def get(self, agent_name):
        """
        الحصول على Agent بالاسم.
        """
        if agent_name not in self.agents:
            raise ValueError(f"Agent '{agent_name}' not found.")

        return self.agents[agent_name]

    def list_agents(self):
        """
        إرجاع قائمة بجميع الـ Agents المسجلين.
        """
        return list(self.agents.keys())

    def broadcast(self, text):
        """
        إرسال نفس الرسالة لكل الـ Agents وتشغيلهم كلّهم.
        """
        results = {}

        for name, agent in self.agents.items():
            try:
                results[name] = agent.safe_run(text)
            except Exception as e:
                results[name] = {"error": str(e)}

        return results

    def subscribe_all(self, message_bus):
        """
        ربط كل Agents بالـ MessageBus تلقائيًا.
        """
        for name, agent in self.agents.items():
            message_bus.subscribe(name, agent)
