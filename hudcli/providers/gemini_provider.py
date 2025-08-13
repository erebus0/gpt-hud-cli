from __future__ import annotations
import os, requests, json
from typing import List, Dict, Any
from .base import Provider

# Google AI Studio (Gemini) - HTTP API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_BASE = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")

class GeminiProvider(Provider):
    name = "gemini"

    def chat(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        model = (kwargs.get("model") or self.model).replace("models/","")
        url = f"{GEMINI_BASE}/models/{model}:generateContent?key={GEMINI_API_KEY}"
        # Map to Gemini 'contents' format
        contents = []
        for m in messages:
            role = "user" if m.get("role")=="user" else "model"
            contents.append({"role": role, "parts": [{"text": m.get("content","")}] })
        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.2),
                "maxOutputTokens": kwargs.get("max_tokens", 1024),
            }
        }
        r = requests.post(url, json=body, timeout=300)
        r.raise_for_status()
        data = r.json()
        # extract text
        text = ""
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            text = ""
        usage = data.get("usageMetadata", {})
        return {"text": text, "usage": usage, "raw": data}

    def supports_tools(self) -> bool:
        # Tool/function calling will be added in Phase 2
        return False
