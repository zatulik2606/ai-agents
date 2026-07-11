from typing import Literal, TypedDict


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class ChatHistory:
    def __init__(self) -> None:
        self._history: dict[int, list[ChatMessage]] = {}

    def get(self, user_id: int) -> list[ChatMessage]:
        return list(self._history.get(user_id, []))

    def add(
        self, user_id: int, role: Literal["user", "assistant"], content: str
    ) -> None:
        if user_id not in self._history:
            self._history[user_id] = []
        self._history[user_id].append({"role": role, "content": content})

    def clear(self, user_id: int) -> None:
        self._history.pop(user_id, None)
