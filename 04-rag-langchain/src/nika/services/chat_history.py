from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


class ChatHistory:
    def __init__(self) -> None:
        self._history: dict[int, list[BaseMessage]] = {}

    def get(self, user_id: int) -> list[BaseMessage]:
        return list(self._history.get(user_id, []))

    def add_user(self, user_id: int, content: str) -> None:
        self._append(user_id, HumanMessage(content=content))

    def add_assistant(self, user_id: int, content: str) -> None:
        self._append(user_id, AIMessage(content=content))

    def clear(self, user_id: int) -> None:
        self._history.pop(user_id, None)

    def _append(self, user_id: int, message: BaseMessage) -> None:
        if user_id not in self._history:
            self._history[user_id] = []
        self._history[user_id].append(message)
