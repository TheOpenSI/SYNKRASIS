# Root folder must have a .env file with HUGGING_FACE_TOKEN
# Ensure you have access to gated models if you intend to use them
# apply chat template - https://huggingface.co/docs/transformers/main/en/chat_templating
# generation prompt - https://huggingface.co/docs/transformers/main/en/chat_templating
# -------------------------------------------------------------------------------

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

import os, warnings
import yaml
import torch
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, pipeline
from huggingface_hub import login
from typing import List, Dict, Optional

# Warning
warnings.filterwarnings('ignore', category=UserWarning, module='torch.utils.checkpoint')

# local imports
from services.Base import ServiceBase
from services.LLM.LLMBase import LLMBase
from utils.output_message_format.output_colour import print_info, print_warning, print_error, print_success, print_model_output

class HF_LLM(ServiceBase, LLMBase):

    def __init__(self,
                 model_name: str = "mistralai/Mistral-7B-v0.1",
                 quantization: str = "4bit",
                 use_cache: bool = True,
                 device_map: str = "auto",
                 max_new_tokens: int = 1024,
                 do_sample: bool = False,
                 top_p: float = 0.95,  # will be ignored if do_sample is False
                 top_k: int = 20,  # will be ignored if do_sample is False
                 temperature: float = 0.7,  # will be ignored if do_sample is False
                 llm_config_file: str = None,  # config file to easily set parameters
                 stop_strings: List[str] = ["\n\nUser:"],
                 # stop strings to stop the generation, default is User: to support default chat template
                 enable_chat_history: bool = False,
                 max_history: int = 3):
        """
        Creates a Huggingface LLM agent
        Args:
            model_name (str): The name of the HF repository, Default : mistral 7B v0.1
            quantization (str): The quantization method to use, 4bit or 8bit, Default : 4bit
            use_cache (bool): use the cached model when loading the model
            device_map (str): The device map to use for loading the model
            max_new_tokens (int): The maximum number of new tokens to generate
            do_sample (bool): Whether to use sampling when generating new tokens, Default : False to make it deterministic
            top_p (float): The top-p value to use when sampling
            top_k (int): The top-k value to use when sampling, the number of highest probability vocabulary tokens to keep for top-k-filtering.
            temperature (float): The temperature value to use when sampling
            llm_config_file (str): The path to a YAML file containing configuration values
            stop_strings (List[str]): Default : ["User:"] which supports the default chat template at /config_files/default_chat_template.txt
            enable_chat_history (bool): Whether to add chat history
            max_history (int): The maximum number of interactions to store in the chat
        """

        # base class
        ServiceBase.__init__(self)
        LLMBase.__init__(self, model_name, enable_chat_history, max_history)
        # Set attributes (config file values will override these)
        self.quantization = quantization
        self.use_cache = use_cache
        self.device_map = device_map
        self.max_new_tokens = max_new_tokens
        self.do_sample = do_sample
        self.top_p = top_p
        self.top_k = top_k
        self.temperature = temperature
        self.hf_token = self._load_hf_token()
        self.seed = 42,
        self.stop_strings = stop_strings

        # login
        self._login_hf()

        # PRIORITY
        # Config from file if provided
        if llm_config_file:
            with open(llm_config_file, "r") as file:
                config = yaml.safe_load(file)
                self.__dict__.update(config)
        self.model = None
        self.tokenizer = None
        self.pipeline = None

        self._initialize_model()
        self._set_seed()


    def _set_seed(self):
        torch.manual_seed(42)
        torch.cuda.manual_seed_all(42)


    def _get_quant_config(self) -> BitsAndBytesConfig:
        if self.quantization == '4bit':
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
            )
        elif self.quantization == '8bit':
            quant_config = BitsAndBytesConfig(load_in_8bit=True)
        else:
            quant_config = None

        return quant_config


    def set_tokenizer(self, add_eos_token: bool = False) -> AutoTokenizer:
        """
        Get the tokenizer from the model repo, can only chage the eos token argument
        Args:
            add_eos_token (bool): Whether to add the eos token to the tokenizer.
            This is useful for finetuning to add eos token to the training data
        """
        tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            add_bos_token=True,
            add_eos_token=add_eos_token,
            padding_side="right"
        )
        tokenizer.pad_token = tokenizer.eos_token

        print_success("Tokenizer initialized")  # DEBUG
        return tokenizer


    def _initialize_model(self):
        # quantization config
        quant_config = self._get_quant_config()

        # tokenizer
        self.tokenizer = self.set_tokenizer()  # don't add eos token for inference

        # model
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=quant_config,
            use_cache=self.use_cache,
            device_map=self.device_map,
            torch_dtype=torch.bfloat16
        )

        # pipeline
        self.pipeline = pipeline(
            model=self.model,
            tokenizer=self.tokenizer, # Check Type
            task="text-generation",
            do_sample=self.do_sample,
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=None,
            repetition_penalty=1.1,
            return_full_text=False,
            max_new_tokens=1024
        )

        print_success("Model initialized")  # DEBUG
        print_info(f"Model name: {self.model.name_or_path.strip().split('/')[-1]}")  # DEBUG


    def _load_hf_token(self) -> str:
        """
        Load the Hugging Face token from the .env file
        """
        # load hf token
        if load_dotenv(os.path.dirname(__file__) + "/../../../.env"):
            hf_token = os.getenv('HUGGING_FACE_TOKEN')
            if not hf_token:
                raise Exception("HUGGING_FACE_TOKEN not found in .env file")

            return hf_token
        else:
            raise Exception("No .env file found")


    def _login_hf(self):
        """
        Login to the Hugging Face Hub
        """
        login(self.hf_token, add_to_git_credential=True)
        print_info("Logged in to Hugging Face Hub")  # DEBUG


    def generate_response(self,
                          user_prompt: str,
                          context: List[str] = None,
                          suppress_conversation_history: bool = True) -> Optional[str]:
        """
        Generate a response to the user prompt
        Args:
            user_prompt (str): The user prompt to generate a response.
            context (str): optional context
            suppress_conversation_history (bool): Whether to send conversation history.
        """
        if not self.model or not self.tokenizer:
            print_error("Model or tokenizer not initialized")
            raise ValueError("Model or tokenizer not initialized")

        context = self._prepare_context(context)
        conversation_history = "" if suppress_conversation_history else self._prepare_conversation_history(user_prompt)
        messages = [{"role": "System", "content": self.system_prompt},
                    {"role": "Conversation", "content": conversation_history},
                    {"role": "Context", "content": context},
                    {"role": "User", "content": user_prompt}]

        prompt = self._prepare_prompt(messages)

        # inference
        response = self.pipeline(prompt,
                                 tokenizer=self.tokenizer,
                                 eos_token_id=self.tokenizer.eos_token_id,
                                 stop_strings=self.stop_strings)

        answer = response[0]["generated_text"].split("User:")[0].strip()

        if self.enable_chat_history:
            if not self.chat_history:
                self.init_chat_history(user_prompt)

            self.chat_history.add_interaction(user_prompt, answer)

        print_model_output(answer, self.model.name_or_path.strip().split("/")[-1])
        return answer


    def cleanup(self):
        """
        Clean up resources and release memory
        """
        if self.model is not None:
            # self.model = self.model.to("cpu") # won't work for quantized models
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        torch.cuda.empty_cache()
        print_success("LLM resources cleaned up.**")

# -------------------------------------------------------------------------------------------------------------

# usage examples:
# basic usage:
# llm = LLMModel()
# response = llm.generate_response("What is the capital of France?")
# print(response)

# custom parameters:
# llm = LLMModel(repo_name="gpt2", quantization="4bit", max_new_tokens=200, temperature=0.8, system_prompt="You are a helpful assistant.")
# response = llm.generate_response("Explain quantum computing.")
# print(response)

# config file:
# llm = LLMModel(llm_config_file="llm_config.yaml")
# response = llm.generate_response("Explain quantum computing.")
# print(response)

# -------------------------------------------------------------------------------------------------------------

# yaml file template
# repo_name: "mistralai/Mathstral-7B-v0.1"
# quantization: "4bit"
# max_new_tokens: 2048
# do_sample: True
# temperature: 0.8
# top_p: 0.92

# -------------------------------------------------------------------------------------------------------------
# .env file template
# HUGGING_FACE_TOKEN = your_hf_token

# -------------------------------------------------------------------------------------------------------------

# if __name__ == "__main__":
#   llm = LLM()