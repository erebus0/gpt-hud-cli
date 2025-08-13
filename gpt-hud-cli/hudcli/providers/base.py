from __future__ import annotations
from typing import List, Dict, Any, Optional, Iterable

Message = Dict[str, Any]

class Provider:
    name: str
    model: str
    def __init__(self, model: str):
        self.model = model

    def chat(self, messages: List[Message], **kwargs) -> Dict[str, Any]:
        """Return { 'text': str, 'usage': {...}, 'raw': {...} }"""
        raise NotImplementedError

    def supports_tools(self) -> bool:
        return False

    def tool_calling(self, messages: List[Message], tools: Iterable[dict], **kwargs) -> Dict[str, Any]:
        raise NotImplementedError("Tool calling not implemented for this provider")
