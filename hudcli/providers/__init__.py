from .base import Provider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider

def make_provider(name: str, model: str) -> Provider:
    name = (name or "openai").lower()
    if name in ("openai", "openai-compatible", "azure"):
        return OpenAIProvider(model)
    if name in ("anthropic", "claude"):
        return AnthropicProvider(model)
    if name in ("gemini", "google", "palm"):
        return GeminiProvider(model)
    return OpenAIProvider(model)
