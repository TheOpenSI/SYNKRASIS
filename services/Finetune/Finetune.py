import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from datasets import load_dataset
from peft.peft_model import PeftModel
from peft import (LoraConfig,
                  prepare_model_for_kbit_training,
                  get_peft_model)
from typing import List, Union

from services.Base import ServiceBase
from services.LLM.HF_LLM.HF_LLM import HF_LLM
from utils.output_message_format.output_colour import print_error, print_warning

class Finetune(ServiceBase):
    def __init__(self,
                 dataset_path: str,
                 model: HF_LLM = None,
                 model_name: str = "mistralai/Mistral-7B-v0.1",
                 target_modules: List[str] = ["q_proj","k_proj","v_proj",
                                              "o_proj","gate_proj","up_proj","down_proj"], # for mistral, set None if peft_config is provided
                 quantization: str = "4bit",
                 use_peft: bool = True,
                 peft_config: LoraConfig = None,
                 format_func: callable = None,
                 dataset_text_field: str = "text"):
        """
        Initialise the Finetune service with base model.
        Either pass the HF_LLM model or model_name to load the model.

        Args:
            dataset_path (str): Fine-tuning dataset path.
            model (HF_LLM, optional): Base model to fine-tune. Defaults to None.
            model_name (str, optional): HF_Repo if no model is passed. Defaults to "mistralai/Mistral-7B-v0.1".
            target_modules (List[str], optional): Target modules. 
                Defaults to ["q_proj","k_proj","v_proj", "o_proj","gate_proj","up_proj","down_proj"].
            quantization (str, optional): Quantization config. Defaults to "4bit".
            use_peft (bool, optional): Use LoRA adapters. Defaults to True.
            peft_config (LoraConfig, optional): LoRA Config. Defaults to None.
            format_func (callable, optional): Dataset formatting function to prepare the dataset and text field. Defaults to None.
            dataset_text_field (str, optional): Dataset text field for training. Defaults to "text".
        """
        super().__init__()
        if model is None:
            self.model: HF_LLM = HF_LLM(model_name = model_name, 
                                        quantization = quantization) # this will login, load tokenizer and quantize model
        else:
            if model.__class__.__name__ != "HF_LLM":
                print_error("Model should be an instance of HF_LLM")
                raise Exception("Model should be an instance of HF_LLM")
            self.model = model
        self.dataset = load_dataset(dataset_path)
        self.use_peft = use_peft
        self.peft_config = peft_config
        self.target_modules = target_modules
        self._apply_dataset_formatting_function(format_func)
        
        
    def _apply_dataset_formatting_function(self, format_func: callable) -> None:
        """
        Apply the dataset formatting function if provided
        """
        if format_func:
            self.dataset = self.dataset.map(format_func, batched = True)
    
    
    def _get_peft_config(self) -> Union[LoraConfig, None]:
        """
        Return the PEFT config or create a default config with r = 32 and lora_alpha = 64
        """
        if self.use_peft:
            if self.peft_config:
                return self.peft_config
            
            return LoraConfig(
                r = 32,
                lora_alpha = 64, # usually double the r
                target_modules = self.target_modules,
                bias = "none",
                lora_dropout = 0.05,
                task_type = "CAUSAL_LM"
            )
        
        return None
    
    
    def _prepare_kbit_quantized_training(self) -> None:
        """
        Preprocess the quantized model for training
        """
        # https://huggingface.co/docs/peft/en/developer_guides/quantization
        # https://huggingface.co/docs/peft/v0.13.0/en/package_reference/peft_model#peft.prepare_model_for_kbit_training
        
        if self.model.quantization:
            self.model = prepare_model_for_kbit_training(self.model)
            
            
    def _create_peft_model(self) -> Union[PeftModel, HF_LLM]:
        """
        Create a PEFT model
        """
        # https://huggingface.co/docs/peft/v0.13.0/en/package_reference/peft_model#peft.PeftModel
        if self.use_peft:
            self.peft_config = self._get_peft_config()
            return get_peft_model(self.model, self.peft_config)
        else:
            print_warning("PEFT is disabled. Using the base model.")
            return self.model