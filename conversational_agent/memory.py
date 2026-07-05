from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Message:
    role: str
    content: str


class ConversationMemory:
    def __init__(self, max_messages: int = 50):
        self._messages: deque[Message] = deque(maxlen=max_messages)

    def add(self, role: str, content: str) -> None:
        self._messages.append(Message(role=role, content=content))

    def get_history(self) -> list[dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self._messages]

    def clear(self) -> None:
        self._messages.clear()

    def last(self) -> Optional[Message]:
        return self._messages[-1] if self._messages else None

    def __len__(self) -> int:
        return len(self._messages)
