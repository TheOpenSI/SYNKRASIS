# root folder must have a .env file with HUGGING_FACE_TOKEN
# ensure you have access to gated models if you intend to use them
#
# Use - 
# llm = LLM()
# llm.set_system_prompt("", read_from_file=True)
# response = llm.generate_response("What is the capital of France?")
# -------------------------------------------------------------------------------

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import os
import torch
import yaml
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from huggingface_hub import login

# local imports
from Services.base import ServiceBase
from utils.output_message_format.output_colour import print_info, print_warning, print_error

class LLM(ServiceBase):
    """
    Creat an LLM agent
    Args:
        repo_name (str): The name of the HF repository, Default : mistral 7B v0.1

        quantization (str): The quantization method to use, 4bit or 8bit, Default : 4bit

        use_cache (bool): use the cached model when loading the model

        device_map (str): The device map to use for loading the model

        max_new_tokens (int): The maximum number of new tokens to generate

        do_sample (bool): Whether to use sampling when generating new tokens, Default : False to make it deterministic
        
        top_p (float): The top-p value to use when sampling

        temperature (float): The temperature value to use when sampling

        config_file (str): The path to a YAML file containing configuration values

        system_prompt (str): will change according to operation
    """
    def __init__(self, 
                 repo_name:str = "mistralai/Mistral-7B-v0.1",
                 quantization:str = "4bit",
                 use_cache:bool = True,
                 device_map:str = "auto",
                 max_new_tokens:int = 1024,
                 do_sample:bool = False,
                 top_p:float = 0.95, # will be ignored if do_sample is False
                 temperature:float = 0.7, # will be ignored if do_sample is False
                 llm_config_file:str = None, # config file to easily set parameters
                 system_prompt:str = "You are a helpful assistant, always answer the question even if the provided context is not helpful",
                 **kwargs):
        
        # base class
        super().__init__()

        # Set attributes (config file values will override these)
        self.repo_name = repo_name
        self.quantization = quantization
        self.use_cache = use_cache
        self.device_map = device_map
        self.max_new_tokens = max_new_tokens
        self.do_sample = do_sample
        self.top_p = top_p
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.hf_token = self.load_hf_token()

        # login
        self.login_hf()

        
        # config from file if provided
        if llm_config_file:
            with open(llm_config_file, "r") as file:
                config = yaml.safe_load(file)
                self.__dict__.update(config)
        
        # llm model
        self.model = None
        self.tokenizer = None
        
        self._initialize_model()
        self.set_seed()


    def set_seed():
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
    

    def _initialize_model(self):
        # quantization config
        quant_config = self._get_quant_config()

        # tokenizer
        self.tokenizer = self.get_tokenizer() # don't add eos token for inference

        # model
        self.model = AutoModelForCausalLM.from_pretrained(
            self.repo_name,
            quantization_config=quant_config,
            use_cache=self.use_cache,
            device_map=self.device_map,
            torch_dtype=torch.bfloat16
        )

    def set_system_prompt(self, prompt:str, read_from_file:bool = False):
        """
        This is to set a custom system prompt duing inference
        Args:
            prompt (str): The system prompt to set

            read_from_file (bool): will read from a file, useful for long prompts

        """
        if read_from_file:
            # TODO: root file variable
            config_file_path = f"{os.path.abspath(__file__)}/../../config_files/system_prompt.txt"
            with open(config_file_path, "r") as file:
                prompt = file.read()
        else:
            self.system_prompt = prompt


    def generate_response(self, user_prompt:str) -> str:
        if not self.model or not self.tokenizer:
            print_error("Model or tokenizer not initialized")
            sys.exit(1) # exit the program with an error code

        inputs = self.prepare_prompt(user_prompt).to(self.model.device)
        
        # inference
        with torch.no_grad():
            output = self.model.generate(
                inputs,
                pad_token_id=self.tokenizer.eos_token_id,
                attention_mask = self.tokenizer,
                max_new_tokens=self.max_new_tokens,
                do_sample=self.do_sample,
                top_p = self.top_p if self.do_sample else None,
                temperature=self.temperature if self.do_sample else None,
                # eos_token_id=self.tokenizer.eos_token_id
            )

        response = self.tokenizer.decode(output[0], skip_special_tokens=True)
        return response.split("Assistant:")[-1].strip()
    

    def load_hf_token(self) -> str:
        """
        Load the Hugging Face token from the .env file
        """
        # load hf token
        if load_dotenv(f"{os.path.abspath(__file__)}/../.."):
            hf_token = os.getenv('HUGGING_FACE_TOKEN')
            if not hf_token:
                raise Exception("HUGGING_FACE_TOKEN not found in .env file")
            
            return hf_token
        else:
            raise Exception("No .env file found")
    

    def login_hf(self):
        """
        Login to the Hugging Face Hub
        """
        login(self.hf_token, add_to_git_credential=True)


    def get_tokenizer(self, add_eos_token:bool = False) -> AutoTokenizer:
        """
        Get the tokenizer from the model repo
        Args:
            add_eos_token (bool): Whether to add the eos token to the tokenizer
            this is useful for finetuning to add eos token to the training data
        """
        tokenizer = AutoTokenizer.from_pretrained(
        self.repo_name,
        add_bos_token = True,
        add_eos_token = add_eos_token,
        padding_side = "left"
        )
        tokenizer.pad_token = self.tokenizer.eos_token

        return tokenizer
    

    def prepare_prompt(self, user_prompt:str) -> str:
        """
        Prepare the prompt for the model, self.tokenizer should be initialized
        Args:
            user_prompt (str): The user prompt to prepare
        """
        # apply chat template - https://huggingface.co/docs/transformers/main/en/chat_templating
        # generation prompt - https://huggingface.co/docs/transformers/main/en/chat_templating
        if self.tokenizer is None:
            print_error("Tokenizer not initialized")
            sys.exit(1)

        messages = [
            {
                "role": "system",
                "content": self.system_prompt,
            },
            {
                "role": "user", 
                "content": user_prompt},
        ]
        return self.tokenizer.apply_chat_template(messages, 
                                                            tokenize=True, 
                                                            add_generation_prompt=True, # must for inference
                                                            return_tensors="pt")

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