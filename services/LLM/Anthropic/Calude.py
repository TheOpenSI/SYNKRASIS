# ====================================================================================
# Anthropic Claude LLM
# Usage:
#    - generate_response(user_prompt: str,
#                        context: List[str] = None,
#                        suppress_conversation_history: bool = True) -> Optional[str]
#    - set_temperature(temperature: float)
#    - set_max_tokens(max_tokens: int)
#    - cleanup():
# ====================================================================================

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

from typing import Optional, Dict, List
import anthropic
from dotenv import load_dotenv

from services.Base import ServiceBase
from services.LLM.LLMBase import LLMBase
from utils.output_message_format.output_colour import print_error, print_info, print_success, print_model_output


class Claude(LLMBase):
    def __init__(self,
                 temperature: float = 1.0,
                 max_tokens: int = 4096,
                 model_name: str = "claude-3-5-sonnet-20241022",
                 enable_chat_history: bool = False,
                 max_history: int = 3,
                 verbose_switch: bool = False):
        """
        Anthropic Claude LLM implementation
        
        Args:
            temperature (float): Controls randomness (0.0 to 1.0). Defaults to 1.0.
            max_tokens (int): Maximum tokens in response. Defaults to 4096.
            model_name (str): Claude model to use. Defaults to "claude-3-5-sonnet-20241022".
            enable_chat_history (bool): Enable conversation history. Defaults to False.
            max_history (int): Maximum interactions to store. Defaults to 3.
            verbose_switch (bool): Enable verbose output. Defaults to False.
        """
        super().__init__(model_name, enable_chat_history, max_history, verbose_switch)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = anthropic.Anthropic(api_key=self._load_anthropic_api_key())


    def _load_anthropic_api_key(self) -> Optional[str]:
        """Load Anthropic API key from environment file"""
        if load_dotenv(f"{os.path.dirname(__file__)}/../../../.env"):
            anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
            if not anthropic_api_key:
                raise Exception("ANTHROPIC_API_KEY not found in .env file")
            return anthropic_api_key
        else:
            raise Exception("No .env file found")
        

    def _get_available_models(self) -> List[str]:
        """
        Get list of available Claude models
        Note: This is a static list as Anthropic doesn't provide a models endpoint
        """
        return [
            "claude-3-7-sonnet-20250219"
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022", 
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]


    def set_model(self, model_name: str):
        """
        Set the Claude model to use
        Args:
            model_name (str): Name of the model to set
        """
        available_models = self._get_available_models()
        if model_name not in available_models:
            print_error(f"Model {model_name} not available. Available models: {available_models}")
            return
        self.model_name = model_name
        print_info(f"Model changed to {self.model_name}")


    def set_temperature(self, temperature: float):
        """Set the temperature for response generation"""
        if not 0.0 <= temperature <= 1.0:
            print_error("Temperature must be between 0.0 and 1.0")
            return
        self.temperature = temperature
        print_info(f"Temperature changed to {self.temperature} for {self.__class__.__name__}")


    def set_max_tokens(self, max_tokens: int):
        """Set maximum tokens for response generation"""
        if max_tokens <= 0:
            print_error("Max tokens must be greater than 0")
            return
        self.max_tokens = max_tokens
        print_info(f"Max tokens changed to {self.max_tokens} for {self.__class__.__name__}")


    def generate_response(self,
                          user_prompt: str,
                          context: List[str] = None,
                          suppress_conversation_history: bool = True) -> Optional[str]:
        """
        Generate response using Claude API
        
        Args:
            user_prompt (str): User query
            context (List[str], optional): RAG context. Defaults to None.
            suppress_conversation_history (bool, optional): Suppress chat history. Defaults to True.
            
        Returns:
            Optional[str]: Claude's response
        """
        try:
            context_str = self._prepare_context(context)
            conversation_history = "" \
                if suppress_conversation_history \
                    else self._prepare_conversation_history(user_prompt)

            # Prepare messages following the same pattern as OpenAI implementation
            messages = [
                {"role": "Conversation", "content": conversation_history},
                {"role": "Context", "content": context_str},
                {"role": "User", "content": user_prompt}
            ]

            # Prepare the full prompt using the base class method
            prompt = self._prepare_prompt(messages)

            if self.verbose_switch:        
                # Print full user query
                print_model_output(prompt, "USER")
                print()

            # Make API call to Claude
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract response content
            answer = response.content[0].text if response.content else None
            
            if not answer:
                print_error("No response received from Claude")
                return None

            # Print the response
            print_model_output(answer, self.model_name)

            # Update chat history if enabled
            if self.enable_chat_history:
                if not self.chat_history:
                    self.init_chat_history(user_prompt)
                self.chat_history.add_interaction(user_prompt, answer)

            return answer

        except anthropic.APIError as e:
            print_error(f"Claude API error: {e}")
            return None
        except Exception as e:
            print_error(f"Error generating response: {e}")
            return None
        

    def cleanup(self):
        """Clean up resources"""
        print_success("Anthropic Claude resources cleaned up.")