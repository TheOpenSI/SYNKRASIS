from abc import ABC, abstractmethod
from typing import List, Optional

class LLMBase(ABC):
    @abstractmethod
    def generate_response(self, 
                          user_prompt: str,
                          context:List[str] = None,
                          suppress_conversation_history:bool = True) -> Optional[str]:
        """
        Generate a response using the LLM
        
        Args:
            user_prompt (str): User query
            context (List[str], optional): RAG context. Defaults to None.
            suppress_conversation_history (bool, optional): Add conversation history. Defaults to True.

        Returns:
            Optional[str]: LLM response
        """
        pass
    
    
    @abstractmethod
    def set_system_prompt(self, system_prompt: str):
        """
        Changes LLM system prompt

        Args:
            system_prompt (str): Desired system prompt
        """
        pass
    
    
    @abstractmethod
    def clear_chat_history(self):
        """
        Clears the chat history
        """
        pass