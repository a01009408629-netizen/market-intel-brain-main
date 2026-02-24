class AgentRegistry:
    def __init__(self):
        self.agents = {}

    def register(self, agent_name, agent_instance):
        if agent_name in self.agents:
            raise ValueError(f"Agent '{agent_name}' already registered.")
        self.agents[agent_name] = agent_instance

    def get(self, agent_name):
        if agent_name not in self.agents:
            raise ValueError(f"Agent '{agent_name}' not found.")
        return self.agents[agent_name]

    def list_agents(self):
        return list(self.agents.keys())

    def broadcast(self, text):
        results = {}
        for name, agent in self.agents.items():
            try:
                results[name] = agent.safe_run(text)
            except Exception as e:
                results[name] = {"error": str(e)}
        return results
