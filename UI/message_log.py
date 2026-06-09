from collections import deque

from UI.colors import Color


class MessageLog:
    def __init__(self, max_messages: int = 4):
        self.max_messages = max_messages
        self._messages: deque[tuple[str, Color]] = deque()

    @property
    def recent(self) -> list[tuple[str, Color]]:
        return list(self._messages)

    def add(self, text: str, color: Color = Color.GRAY):
        self._messages.append((text, color))
        while len(self._messages) > self.max_messages:
            self._messages.popleft()
