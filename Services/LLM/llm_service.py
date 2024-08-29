# -------------------------------------------------------------------------------------------------------------
# File: llm_service.py
# Project: Synkrasis
# Contributors:
#     Muntasir Adnan <adnan.adnan@canberra.edu.au>
# 
# Copyright (c) 2024 Adnan525
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without
# limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so, subject to the following
# conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial
# portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
# LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# -------------------------------------------------------------------------------------------------------------

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import os
import torch
import yaml
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from huggingface_hub import login

from utils.log_tool import set_color
from src.services.base import ServiceBase


class LLMModel(ServiceBase):
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
                 llm_config_file:str = None,
                 system_prompt:str = "You are a helpful assistant, always answer the question even if the provided context is not helpful",
                 **kwargs):
        
        super().__init__(**kwargs)

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
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.repo_name,
            add_bos_token=True,
            padding_side="left"
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token

        # model
        self.model = AutoModelForCausalLM.from_pretrained(
            self.repo_name,
            quantization_config=quant_config,
            use_cache=self.use_cache,
            device_map=self.device_map,
            torch_dtype=torch.bfloat16
        )

    # def set_system_prompt(self, prompt):
    #     self.system_prompt = prompt


    def generate_response(self, user_prompt:str) -> str:
        if not self.model or not self.tokenizer:
            print(set_color("error", "Model and tokenizer are not initialized."))
            sys.exit()

        full_prompt = f"System: {self.system_prompt}\nUser: {user_prompt}\nAssistant:"
        inputs = self.tokenizer(full_prompt, return_tensors="pt", padding=True).input_ids.to("cuda:0")
        with torch.no_grad():
            output = self.model.generate(
                inputs,
                pad_token_id=self.tokenizer.eos_token_id,
                attention_mask = torch.where(inputs == 2, 0, 1),
                max_new_tokens=self.max_new_tokens,
                do_sample=self.do_sample,
                top_p = self.top_p if self.do_sample else None,
                temperature=self.temperature if self.do_sample else None,
                # eos_token_id=self.tokenizer.eos_token_id
            )

        response = self.tokenizer.decode(output[0], skip_special_tokens=True)
        return response.split("Assistant:")[-1].strip()
    

    def load_hf_token(self) -> str:
        # load hf token
        if load_dotenv():
            hf_token = os.getenv('HUGGING_FACE_TOKEN')
            if not hf_token:
                print(set_color("error", "HUGGING_FACE_TOKEN not found in .env file")) # TODO: raise exception
        else:
            print(set_color("error", "HUGGING_FACE_TOKEN not found. Pleresponsease ensure it's set in your environment or in a .env file.")) # TODO: raise exception
        
        return hf_token
    

    def login_hf(self):
        login(self.hf_token, add_to_git_credential=True)

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
#   # llm = LLMModel()
#   # response = llm.generate_response("")