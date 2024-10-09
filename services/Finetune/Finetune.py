import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from datasets import load_dataset
from peft import (LoraConfig,
                  prepare_model_for_kbit_training,
                  get_peft_model)
from typing import List

from services.Base import ServiceBase
from services.LLM.HF_LLM.HF_LLM import HF_LLM

class Finetune(ServiceBase):
    def __init__(self,
                 dataset_path: str,
                 model_name: str = "mistralai/Mistral-7B-v0.1",
                 target_modules: List[str] = ["q_proj","k_proj","v_proj",
                                              "o_proj","gate_proj","up_proj","down_proj"], # for mistral, set None if peft_config is provided
                 quantization: bool = "4bit",
                 use_peft: bool = True,
                 peft_config: LoraConfig = None):
        super().__init__()
        self.model: HF_LLM = HF_LLM(model_name=model_name, quantization=quantization) # this will login, load tokenizer and quantize model
        self.dataset = load_dataset(dataset_path)
        self.use_peft = use_peft
        self.peft_config = peft_config
        self.target_modules = target_modules
        
        
    def _get_defult_peft_config(self):
        """
        Setting PEFT or LoRA config
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
            
            
    def _create_peft_model(self):
        """
        Create a PEFT model
        """
        return get_peft_model(self.model, self.peft_config)