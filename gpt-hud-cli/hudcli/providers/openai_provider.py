from __future__ import annotations
import os, requests, json
from typing import List, Dict, Any
from .base import Provider

OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

class OpenAIProvider(Provider):
    name = "openai-compatible"

    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        model = kwargs.get("model") or self.model
        stream = bool(kwargs.get("stream", False))
        url = f"{OPENAI_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 1024),
            "stream": stream,
        }
        r = requests.post(url, headers=headers, data=json.dumps(body), timeout=300)
        r.raise_for_status()
        data = r.json()
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})
        return {"text": text, "usage": usage, "raw": data}

    # Some OpenAI-compatible backends support tools/function_call
    def supports_tools(self) -> bool:
        return True

    def tool_calling(self, messages, tools, **kwargs):
        model = kwargs.get("model") or self.model
        url = f"{OPENAI_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": messages,
            "tools": list(tools),
            "tool_choice": kwargs.get("tool_choice", "auto"),
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 1024),
        }
        r = requests.post(url, headers=headers, json=body, timeout=300)
        r.raise_for_status()
        return {"text": (r.json().get("choices") or [{}])[0].get("message", {}).get("content", ""),
                "usage": r.json().get("usage", {}),
                "raw": r.json()}
