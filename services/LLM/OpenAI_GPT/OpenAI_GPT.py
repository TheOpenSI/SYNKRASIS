import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

from typing import Optional, Dict, List
from openai import OpenAI
from dotenv import load_dotenv

from services.Base import ServiceBase
from services.LLM.LLMBase import LLMBase
from utils.output_message_format.output_colour import print_error, print_info, print_success, print_model_output

class OpenAI_GPT(ServiceBase, LLMBase):
    def __init__(self,
                 temperature: float = 0.7,
                 seed: int = 42, 
                 model: str = "gpt-3.5-turbo",
                 enable_chat_history: bool = False):
        ServiceBase.__init__(self)
        LLMBase.__init__(self, enable_chat_history=enable_chat_history)
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.client: OpenAI = OpenAI(api_key=self._load_openai_api_key())
        

    def _load_openai_api_key(self) -> Optional[str]:
        if load_dotenv(f"{os.path.dirname(__file__)}/../../../.env"):
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise Exception("OPENAI_API_KEY not found in .env file")
            return openai_api_key
        else:
            raise Exception("No .env file found")


    def set_temperature(self, temperature: float):
        self.temperature = temperature
        print_info(f"Temperature changed to {self.temperature} for {self.__class__.__name__}")


    def generate_response(self, 
                          user_prompt: str,
                          context: List[str] = None,
                          suppress_conversation_history: bool = True) -> Optional[str]:
        context_str = self._prepare_context(context)
        conversation_history = "" if suppress_conversation_history else self._prepare_conversation_history(user_prompt)

        # For openai, we send the system prompt separately
        messages = [
            {"role": "Conversation", "content": conversation_history},
            {"role": "User", "content": user_prompt},
            {"role": "Context", "content": context_str} # changing the order
        ]

        prompt = self._generate_prompt(messages)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
                ],
            temperature=self.temperature,
            seed=self.seed
        )
        
        # TODO: For finetune data
        print("="*50)
        print(f"[FINAL PROMPT] {prompt}")
        print("="*50)

        answer = response.choices[0].message.content
        print_model_output(answer, self.model)

        if self.enable_chat_history and self.chat_history:
            self.chat_history.add_interaction(user_prompt, answer)

        return answer


    def cleanup(self):
        print_success("OpenAI GPT resources cleaned up.")