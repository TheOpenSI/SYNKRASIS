import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

from typing import Optional, Dict, List
from openai import OpenAI
from dotenv import load_dotenv

from services.Base import ServiceBase
from services.LLM.LLMBase import LLMBase
from modules.ChatHistory import ChatHistory
from utils.output_message_format.output_colour import print_error, print_info, print_success, print_model_output

class OpenAI_GPT(ServiceBase, LLMBase):
    # Seed and temperature issue https://community.openai.com/t/seed-param-and-reproducible-output-do-not-work/487245
    # Non-deterministic embedding - https://community.openai.com/t/non-deterministic-embedding-results-using-text-embedding-ada-002/74733
    
    def __init__(self,
                temperature: float = 0.7,
                seed: int = 42, 
                model: str = "gpt-3.5-turbo", 
                enable_chat_history:bool = False):  # uses gpt-3.5-turbo as default model
        """
        LLM service using OpenAI API

        Args:
            model (str, optional): Model name. Defaults to "gpt-3.5-turbo".
            enable_chat_history (bool, optional): Chat History. Defaults to False.
        """
        super().__init__()
        self.model = model
        self.enable_chat_history = enable_chat_history
        self.system_prompt = "Always answer the question to the best of your ability even if the context is not useful."
        self.temperature = temperature
        self.seed = seed
        self.chat_history: ChatHistory = None
        self.client: OpenAI = OpenAI(api_key = self._load_openai_api_key())

    
    def _load_openai_api_key(self) -> Optional[str]:
        """
        Load the Hugging Face token from the .env file
        """
        # load hf token
        if load_dotenv(f"{os.path.dirname(__file__)}/../../../.env"):
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise Exception("OPENAI_API_KEY not found in .env file")
            
            return openai_api_key
        else:
            raise Exception("No .env file found")
        
        
    def _init_chat_history(self, original_question: str, max_history: int = 1):
        """
        Initialize the chat history with the original question.
        Should be used only if enable_chat_history is set to True.
        Args:
            original_question (str): The initial question to start the chat.
            max_history (int): Maximum number of interactions to store in history.
        """
        self.chat_history = ChatHistory(original_question, max_history)
        
    
    def set_temperature(self, temperature: float):
        """
        Change the temperature of the model
        Args:
            temperature (float): The new temperature value
        """
        self.temperature = temperature
        print_info(f"Temperature changed to {self.temperature} for {self.__class__.__name__}")
        
        
    def set_system_prompt(self, system_prompt: str):
        """
        Change the system prompt
        Args:
            system_prompt (str): The new system prompt
        """
        self.system_prompt = system_prompt
            

    def generate_response(self, 
                          user_prompt: str,
                          context:List[str] = None,
                          suppress_conversation_history:bool = True) -> Optional[str]:
        """
        Generate a response using the OpenAI API

        Args:
            user_prompt (str): The user prompt
            context (List[str], optional): Context for RAG. Defaults to None.
            suppress_conversation_history (bool, optional): Add conversation history. Defaults to True.

        Returns:
            Optional[str]: Response from the model
        """
        # TODO: No context or conversation history support for the time being.
        # TODO: Use the jinja template to generate the prompt.
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            seed = self.seed
        )
        
        print_model_output(response.choices[0].message.content, self.model)
        return response.choices[0].message.content


    def clear_chat_history(self):
        """
        Clear the chat history, happens automatically when system prompt changes.
        """
        if self.enable_chat_history:
            self.chat_history = None
            print_success("Chat history cleared.")
        else:
            print_error("Chat history is not enabled.") 
             
    
    def cleanup(self):
        """
        Nothing to cleanup for OpenAI GPT
        """
        print_success("OpenAI GPT resources cleaned up.")
    