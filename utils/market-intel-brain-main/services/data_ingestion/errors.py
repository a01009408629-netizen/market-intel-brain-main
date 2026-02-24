from typing import Optional
import traceback
import datetime


class MAIFAError(Exception):
    """
    MAIFA Titanium Standard Error Contract
    All errors MUST flow through this class or its subclasses.
    No raw exceptions allowed anywhere in the 13-source pipeline.
    """

    def __init__(
        self,
        source: str,
        stage: str,
        error_type: str,
        message: str,
        retryable: bool,
        details: Optional[str] = None
    ):
        self.source = source
        self.stage = stage
        self.error_type = error_type
        self.message = message
        self.retryable = retryable
        self.details = details or traceback.format_exc()
        self.timestamp = datetime.datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            "source": self.source,
            "stage": self.stage,
            "status": "error",
            "error_type": self.error_type,
            "message": self.message,
            "retryable": self.retryable,
            "timestamp": self.timestamp,
            "details": self.details
        }


class FetchError(MAIFAError): pass
class ValidationError(MAIFAError): pass
class NormalizationError(MAIFAError): pass
