import os
import sqlite3
from cryptography.fernet import Fernet, InvalidToken
from datetime import datetime
from queue import Queue
import threading

# -----------------------------
# Logger بسيط وفعال (Single Worker)
# -----------------------------
class AsyncLogger:
    def __init__(self):
        self.queue = Queue()
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        while True:
            msg = self.queue.get()
            print(f"{datetime.utcnow().isoformat()} | {msg}")
            self.queue.task_done()

    def log(self, agent, msg):
        self.queue.put(f"{agent} | {msg}")

logger = AsyncLogger()

# -----------------------------
# BrainDatabase (المحسن للعمليات الضخمة)
# -----------------------------
class BrainDatabase:
    def __init__(self, db_path="brain_encrypted.db"):
        self.db_path = db_path
        self.current_key_id = os.getenv("BRAIN_KEY_ID", "v1")
        key_str = os.getenv("BRAIN_KEY")
        if not key_str:
            raise EnvironmentError("CRITICAL: BRAIN_KEY missing.")
        self.cipher = Fernet(key_str.encode())
        self._bootstrap()

    def _bootstrap(self):
        with self._get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL;") # تحسين أداء الكتابة والقراءة المتزامنة
            conn.execute("""
                CREATE TABLE IF NOT EXISTS brain_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT,
                    timestamp DATETIME,
                    key_id TEXT,
                    encrypted_message BLOB
                )
            """)

    def _get_conn(self):
        return sqlite3.connect(self.db_path, timeout=30)

    def save_message(self, agent_name: str, message: str):
        """حفظ رسالة واحدة"""
        self.save_bulk(agent_name, [message])

    def save_bulk(self, agent_name: str, messages: list):
        """حفظ مجموعة رسائل في معاملة (Transaction) واحدة - أسرع بـ 100 مرة"""
        if not messages: return
        
        prepared_data = []
        now = datetime.utcnow()
        for msg in messages:
            encrypted = self.cipher.encrypt(msg.encode())
            prepared_data.append((agent_name, now, self.current_key_id, encrypted))

        try:
            with self._get_conn() as conn:
                conn.executemany(
                    "INSERT INTO brain_data (agent_name, timestamp, key_id, encrypted_message) VALUES (?, ?, ?, ?)",
                    prepared_data
                )
            logger.log(agent_name, f"Bulk saved {len(messages)} messages.")
        except Exception as e:
            logger.log(agent_name, f"Bulk Write Fail: {e}")

    def read_messages(self):
        results = []
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT agent_name, timestamp, encrypted_message FROM brain_data")
            for row in cursor:
                try:
                    decrypted = self.cipher.decrypt(row[2]).decode()
                    results.append({"agent": row[0], "time": row[1], "message": decrypted})
                except InvalidToken:
                    continue
        return results
