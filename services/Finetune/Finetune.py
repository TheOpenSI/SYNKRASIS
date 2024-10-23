import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import yaml, torch
from datasets import load_dataset
from peft.peft_model import PeftModel
from peft import (LoraConfig,
                  prepare_model_for_kbit_training,
                  get_peft_model)
from typing import List, Union
from trl import SFTTrainer, SFTConfig

from services.Base import ServiceBase
from services.LLM.HF_LLM.HF_LLM import HF_LLM
from utils.output_message_format.output_colour import print_error, print_warning, print_model_output, print_success

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
                 training_args_path = "config_files/finetune_config.yaml"):
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
            training_args_path (str, optional): SFTConfig arguments.
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
        self.training_args_path = training_args_path
        self._apply_dataset_formatting_function(format_func)
        self.finetuned_model = None
        
        
    def _apply_dataset_formatting_function(self, format_func: callable) -> None:
        """
        Apply the dataset formatting function if provided.
        This will ideally make the "text" field ready for training.
        """
        if format_func:
            self.dataset = self.dataset.map(format_func, batched = True)
    
    
    def _get_peft_config(self) -> Union[LoraConfig, None]:
        # https://discuss.huggingface.co/t/task-type-parameter-of-loraconfig/52879/6
        # https://github.com/huggingface/peft/blob/v0.8.2/src/peft/utils/peft_types.py#L68-L73
        # https://medium.com/@tom_21755/understanding-causal-llms-masked-llm-s-and-seq2seq-a-guide-to-language-model-training-d4457bbd07fa
        
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
        
    
    def _load_finetune_sft_config_args(self) -> dict:
        """
        Load the sftconfig arguments from the config file and returns as a dictionary
        """
        with open(self.training_args_path, "r") as file:
            sft_config_args = yaml.safe_load(file)
        
        return sft_config_args
        
        
    def _get_training_args(self) -> SFTConfig:
        """
        Get the SFTConfig for SFTTrainer

        Returns:
            SFTConfig: SFTTrainer args, reads from a yaml config file.
        """
        sft_config_args = self._load_finetune_training_args()
        return SFTConfig(**sft_config_args)
    
    
    def train(self, push_to_hub: bool = False, hub_repo_name: str = None) -> None:
        """
        Train the model with the fine-tuning dataset
        Args:
            push_to_hub (bool, optional): Push the model to the hub. Defaults to False.
            hub_repo_name (str, optional): Hub repo name. Defaults to None.
        """
        self._prepare_kbit_quantized_training()
        model = self._create_peft_model() # does not chnage the self.model object
        sft_config = self._get_training_args()
        trainer = SFTTrainer(model = model,
                             tokenizer = model.tokenizer, 
                             train_dataset = self.dataset["train"], 
                             peft_config = self._get_peft_config,
                             args = sft_config)
        trainer.train()
        self.finetuned_model = model
        trainer.save_model()
        if push_to_hub:
            if hub_repo_name is None:
                raise Exception("Please provide the hub_repo_name to push the model to the hub.")   
            self.finetuned_model.push_to_hub(hub_repo_name)
            
    
    def generate_response(self, user_prompt: str) -> str:
        """
        Generate a response from the fine-tuned model
        """
        if self.finetuned_model is None:
            raise Exception("Model is not fine-tuned yet. Please train the model first.")
        self.finetuned_model.eval()
        
        # Tokenizer
        inputs = self.model.tokenizer(user_prompt, add_special_tokens = False, return_tensors = "pt", padding = True)
        with torch.inference_mode():
            outputs = self.finetuned_model.generate(
                input_ids = inputs["input_ids"],
                attention_mask = inputs["attention_mask"],
                max_new_tokens = 1024,
                do_sample = True,
                top_p = 0.9,
                temperature = 0.5
            )
        response = self.model.tokenizer.decode(outputs[0], skip_special_tokens=True)
        print_model_output(response, f"FINE-TUNED {self.model.model_name}")
        return response
    
    
    def cleanup(self):
        self.model.cleanup()
        print_success("Finetune resources cleaned up.")