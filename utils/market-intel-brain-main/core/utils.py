import uuid
import time


def generate_id() -> str:
    """معرّف فريد للمهام أو الرسائل."""
    return str(uuid.uuid4())


def timestamp() -> float:
    """وقت UNIX الحالي."""
    return time.time()


def safe_dict_get(data: dict, key: str, default=None):
    """قراءة آمنة من القواميس."""
    return data[key] if key in data else default
