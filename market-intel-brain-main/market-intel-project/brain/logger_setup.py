import logging
import os

def get_logger(name: str) -> logging.Logger:
    """
    يُنشئ Logger مركزي للمشروع.
    كل الـ Agents يستخدمونه لتسجيل الأحداث.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # منع التكرار في حالة استدعاء Logger أكثر من مرة
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    logger.propagate = False

    return logger
