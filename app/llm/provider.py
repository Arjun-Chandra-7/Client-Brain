from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Boundary for optional LLM work; canonical records are always persisted by services."""
    @abstractmethod
    def extract_structured_information(self, text: str) -> list[dict]: ...
    @abstractmethod
    def generate_insights(self, evidence: list[dict]) -> list[dict]: ...
    @abstractmethod
    def answer_question(self, question: str, context: dict) -> str | None: ...


class NoopLLMProvider(LLMProvider):
    """Safe offline default: it returns no invented extraction, inference, or answer."""
    def extract_structured_information(self, text: str) -> list[dict]: return []
    def generate_insights(self, evidence: list[dict]) -> list[dict]: return []
    def answer_question(self, question: str, context: dict) -> str | None: return None
