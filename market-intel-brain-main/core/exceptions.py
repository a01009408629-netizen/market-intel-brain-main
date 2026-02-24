class AgentError(Exception):
    """خطأ عام للـ Agents."""
    pass


class BrainError(Exception):
    """خطأ متعلق بالـ Brain."""
    pass


class ValidationError(Exception):
    """خطأ متعلق بالمدخلات أو البيانات."""
    pass
