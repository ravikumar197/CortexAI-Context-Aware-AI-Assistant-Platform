
import os

import ollama


class OllamaProvider:
    """AI provider that runs inference through a local Ollama model."""

    def __init__(self) -> None:
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        self.client = ollama.Client(
            host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        )

    def generate(self, prompt: str) -> str:
        """Generate a response from the local model."""
        response = self.client.generate(
            model=self.model,
            prompt=prompt,
        )
        return response.response.strip()


def get_ai_provider() -> OllamaProvider:
    """Return the configured AI provider."""
    return OllamaProvider()
