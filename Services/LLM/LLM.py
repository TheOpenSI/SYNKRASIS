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
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, pipeline
from huggingface_hub import login
from typing import List, Dict

# local imports
from Services.base import ServiceBase
from utils.output_message_format.output_colour import print_info, print_warning, print_error

class LLM(ServiceBase):

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
                 stop_strings:List[str] = ["\n\nUser:"], # stop strings to stop the generation, default is User: to supoort default chat template
                 ):
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
            stop_strings (List[str]): Default : ["User:"] which supports the default chat template at /config_files/default_chat_template.txt
        """
        
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
        self.hf_token = self._load_hf_token()
        self.seed = 42,
        self.stop_strings = stop_strings

        # login
        self._login_hf()

        
        # config from file if provided
        if llm_config_file:
            with open(llm_config_file, "r") as file:
                config = yaml.safe_load(file)
                self.__dict__.update(config)
        
        # llm model
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
    

    def _initialize_model(self):
        # quantization config
        quant_config = self._get_quant_config()

        # tokenizer
        self.tokenizer = self.set_tokenizer() # don't add eos token for inference

        # model
        self.model = AutoModelForCausalLM.from_pretrained(
            self.repo_name,
            quantization_config=quant_config,
            use_cache=self.use_cache,
            device_map=self.device_map,
            torch_dtype=torch.bfloat16
        )

        # pipeline
        self.pipeline = pipeline(
        model = self.model,
        tokenizer = self.tokenizer,
        task = "text-generation",
        do_sample = False,
        repetition_penalty = 1.1,
        return_full_text = False,
        max_new_tokens = 1024
        )

        print_info("Model initialized")
        print_info(f"Model name: {self.repo_name.strip()}")


    def _prepare_chat_template(self, messages:List[Dict[str, str]]):
        """
        This will apply a default chat template if the tokenizer does not support it.
        If chat template is not supported and no default template is provided, will retun a value error
        """
        # if self.tokenizer.chat_template is None: # TODO: setting default chat template for all models
        print_warning("Chat template not supported by the tokenizer, applying default template")
        default_prompt_path = os.path.abspath(__file__).replace("llm_service.py", "../../config_files/default_chat_template.jinja")
        with open(default_prompt_path, "r") as file:
            default_prompt = file.read()
            self.tokenizer.chat_template = default_prompt # always has generation prompt

        return self.tokenizer.apply_chat_template(messages, 
                                                tokenize=False, 
                                                add_generation_prompt=True) # wont work for all models
    

    def _prepare_prompt(self, user_prompt:str) -> str:
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
                "role": "System",
                "content": self.system_prompt,
            },
            {
                "role": "User", 
                "content": user_prompt},
        ]

        # Encoding separately to get the attention mask all in one go
        prompt = self._prepare_chat_template(messages)

        # return self.tokenizer(prompt, return_tensors="pt", padding=True)
        return prompt # resturn string to use with pipeline
    

    def _load_hf_token(self) -> str:
        """
        Load the Hugging Face token from the .env file
        """
        # load hf token
        if load_dotenv(f"{os.path.abspath(__file__).replace('llm_service.py', '')}../../.env"):
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
        print_info("Logged in to Hugging Face Hub")


    def set_system_prompt(self, prompt:str, read_from_file:bool = False):
        """
        This is to set a custom system prompt duing inference
        Args:
            prompt (str): The system prompt to set

            read_from_file (bool): will read from a file, useful for long prompts

        """
        if read_from_file:
            # TODO: root file variable
            prompt_file_path = f"{os.path.abspath(__file__)}/../../config_files/system_prompt.txt"
            with open(prompt_file_path, "r") as file:
                prompt = file.read()
        else:
            self.system_prompt = prompt


    def generate_response(self, user_prompt:str) -> str:
        """
        Generate a response to the user prompt
        Args:
            user_prompt (str): The user prompt to generate a response to
        """
        if not self.model or not self.tokenizer:
            print_error("Model or tokenizer not initialized")
            sys.exit(1) # exit the program with an error code

        prompt = self._prepare_prompt(user_prompt)
        
        # inference
        response = self.pipeline(prompt, 
                                 tokenizer = self.tokenizer,
                                 eos_token_id = self.tokenizer.eos_token_id,
                                 stop_strings = self.stop_strings)
        
        return response[0]["generated_text"].split("User:")[0].strip()
    

    def set_tokenizer(self, add_eos_token:bool = False) -> AutoTokenizer:
        """
        Get the tokenizer from the model repo, can only chage the eos token argument
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
        tokenizer.pad_token = tokenizer.eos_token
        
        print_info("Tokenizer initialized")
        return tokenizer
    

    def cleanup(self):
        """
        Clean up resources and release memory
        """
        print_info("Cleaning up LLM resources...")
        if self.model is not None:
            # self.model = self.model.to("cpu") # won't work for quantized models
            del self.model 
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        torch.cuda.empty_cache()
        print_success("LLM resources cleaned up.") 

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