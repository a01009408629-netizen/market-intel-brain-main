
import hashlib
import json
from typing import Any, Dict

class MAIFAFingerprint:
    __slots__ = ()

    @staticmethod
    def build(source: str, params: Dict[str, Any]) -> str:
        if type(params) is not dict:
            params = {}

        source = source.strip()

        try:
            # Tuple serialization for ultra-low memory overhead
            serialized = json.dumps(
                (source, params),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":")
            ).encode("utf-8")
        except TypeError:
            # Zero-Crash constraint: Fallback for non-serializable objects (datetime, UUID, etc.)
            safe_params = {str(k): str(v) for k, v in params.items()}
            serialized = json.dumps(
                (source, safe_params),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":")
            ).encode("utf-8")

        return hashlib.sha256(serialized).hexdigest()
