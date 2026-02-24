import queue
import threading
import traceback


class MessageBus:
    def __init__(self):
        self.message_queue = queue.Queue()
        self.subscribers = {}
        self.running = False
        self.worker_thread = None

    def start(self):
        if self.running:
            return

        self.running = True
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True
        )
        self.worker_thread.start()

    def stop(self):
        self.running = False

    def _worker_loop(self):
        while self.running:
            try:
                agent_name, message = self.message_queue.get(timeout=1)

                if agent_name in self.subscribers:
                    agent = self.subscribers[agent_name]
                    try:
                        agent.safe_run(message)
                    except Exception:
                        traceback.print_exc()

            except queue.Empty:
                continue

    def subscribe(self, agent_name, agent_instance):
        self.subscribers[agent_name] = agent_instance

    def send(self, agent_name, message):
        if agent_name not in self.subscribers:
            raise ValueError(f"Agent '{agent_name}' not subscribed to message bus")

        self.message_queue.put((agent_name, message))

    def broadcast(self, message):
        for agent_name in self.subscribers:
            self.message_queue.put((agent_name, message))
