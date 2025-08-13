from __future__ import annotations
import os, requests, json
from typing import List, Dict, Any
from .base import Provider

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_VERSION = os.environ.get("ANTHROPIC_VERSION", "2023-06-01")  # may be overridden

class AnthropicProvider(Provider):
    name = "anthropic"

    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        model = kwargs.get("model") or self.model
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": ANTHROPIC_API_KEY or "",
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        # Map OpenAI-style roles to Anthropic's (user/assistant only)
        mapped: list = []
        for m in messages:
            role = m.get("role")
            if role == "system":
                # system in Anthropic v1 lives in a top-level 'system' field
                continue
            mapped.append({"role": "user" if role == "user" else "assistant",
                           "content": m.get("content","")})
        system_text = next((m.get("content","") for m in messages if m.get("role")=="system"), None)
        body = {
            "model": model,
            "messages": mapped,
            "max_tokens": kwargs.get("max_tokens", 1024),
            "temperature": kwargs.get("temperature", 0.2),
        }
        if system_text:
            body["system"] = system_text
        r = requests.post(url, headers=headers, data=json.dumps(body), timeout=300)
        r.raise_for_status()
        data = r.json()
        text = "".join([(p.get("text") or "") for p in (data.get("content") or []) if p.get("type")=="text"])
        usage = data.get("usage", {})
        return {"text": text, "usage": usage, "raw": data}

    def supports_tools(self) -> bool:
        # Anthropic Messages API supports tools; implement later
        return False  # stub for Phase 1
