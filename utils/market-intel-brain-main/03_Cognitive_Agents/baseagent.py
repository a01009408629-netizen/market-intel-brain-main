import abc
import logging


class BaseAgent(abc.ABC):
    """
    القالب الأساسي لجميع الوكلاء.
    حماية صارمة ضد أي تعديل غير مصرح.
    """

    _protected = True  # علامة حماية

    def __init__(self, name: str, logger: logging.Logger):
        if not getattr(self, "_protected", False):
            raise RuntimeError("BaseAgent تم التلاعب به!")
        self.name = name
        self.logger = logger

    @abc.abstractmethod
    def run(self, data=None) -> dict:
        """كل Agent يجب أن يطبّق هذه الدالة"""
        pass

    def log(self, msg: str):
        """تسجيل الأحداث"""
        if self.logger:
            self.logger.info(f"[{self.name}] {msg}")

    def _check_integrity(self):
        """حماية داخلية ضد التغييرات العشوائية"""
        if not getattr(self, "_protected", False):
            raise RuntimeError(f"{self.name} تم تعديل BaseAgent بشكل غير مسموح!")


# Alias for backward compatibility
AgentBase = BaseAgent
