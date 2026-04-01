import os
from dataclasses import dataclass


@dataclass(slots=True)
class InterpreterSettings:
    mode: str = "auto"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout_seconds: int = 60


def get_settings() -> InterpreterSettings:
    return InterpreterSettings(
        mode=os.getenv("INTERPRETER_MODE", "auto").strip().lower() or "auto",
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip(),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b").strip(),
        ollama_timeout_seconds=int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60")),
    )
