from abc import ABC, abstractmethod
from typing import List, Optional

class LLMBase(ABC):
    @abstractmethod
    def generate_response(self, 
                          user_prompt: str,
                          context:List[str] = None,
                          suppress_conversation_history:bool = True) -> Optional[str]:
        pass