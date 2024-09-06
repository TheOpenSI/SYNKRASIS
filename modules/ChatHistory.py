import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

from typing import List, Dict, Tuple, Optional
from collections import deque

from utils.output_message_format.output_colour import print_info, print_warning


class ChatHistory:
    def __init__(self, original_question: str, max_history: int = 3):
        if not isinstance(original_question, str) or "" == original_question.strip():
            raise ValueError("Original question must be a non-empty string")
        if not isinstance(max_history, int) or max_history < 1:
            raise ValueError("max_history must be a positive integer")

        self._original_question: Optional[str] = original_question
        self._max_history: int = max_history
        self._conversation_history: deque[Tuple[str, str]] = deque(maxlen=max_history)

    @property
    def original_question(self) -> Optional[str]:
        # This just returns the original question
        if self._original_question is None or "" == self._original_question.strip():
            print_warning("Original question has not been set")
        return self._original_question

    @property
    def conversation_history(self) -> List[Tuple[str, str]]:
        return list(self._conversation_history)

    @property
    def history_length(self) -> int:
        return len(self._conversation_history)

    @property
    def last_question(self) -> Optional[str]:
        if self._conversation_history:
            return self._conversation_history[-1][0]
        return self._original_question

    def add_interaction(self, question: str, answer: str) -> None:
        if not isinstance(question, str) or "" == question.strip():
            raise ValueError("Question must be a non-empty string")
        if not isinstance(answer, str) or "" == answer.strip():
            raise ValueError("Answer must be a non-empty string")

        self._conversation_history.append((question, answer))
        # No need to manually manage the deque size, as it's handled by maxlen

    def clear_history(self) -> None:
        self._original_question = None
        self._conversation_history = deque(maxlen=self._max_history)

    def to_dict(self) -> Dict[str, any]:
        return {
            "original_question": self._original_question,
            "conversation_history": list(self._conversation_history)
        }

    def __str__(self) -> str:
        return f"ChatHistory(original_question='{self._original_question}', history_length={len(self._conversation_history)})"

    def __repr__(self) -> str:
        return (
            f"ChatHistory("
            f"original_question={repr(self._original_question)} (type={type(self._original_question).__name__}), "
            f"max_history={self._max_history} (type={type(self._max_history).__name__}), "
            f"conversation_history={list(self._conversation_history)} (type={type(self._conversation_history).__name__}), "
            f"history_length={len(self._conversation_history)}"
            f")"
        )
