# =========================================================================================
# Root folder must have a .env file with HUGGING_FACE_TOKEN
# Ensure you have access to gated models if you intend to use them
# apply chat template - https://huggingface.co/docs/transformers/main/en/chat_templating
# generation prompt - https://huggingface.co/docs/transformers/main/en/chat_templating
# Usage:
#     - set_tokenizer(add_eos_token: bool = False) -> AutoTokenizer
#     - generate_response(user_prompt: str, 
#                         context: List[str] = None, 
#                         suppress_conversation_history: bool = True) -> Optional[str]
#     - cleanup():
# =========================================================================================

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../..")

import os, warnings
import yaml
import torch
from dotenv import load_dotenv
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    BitsAndBytesConfig, 
    pipeline
)
from huggingface_hub import login
from jinja2.exceptions import TemplateError
from typing import List, Dict, Optional

warnings.filterwarnings('ignore', category=UserWarning, module='torch.utils.checkpoint')

from services.LLM.LLMBase import LLMBase
from utils.output_message_format.output_colour import print_info, print_warning, print_error, print_success, print_model_output

class HF_LLM(LLMBase):

    def __init__(self,
                 model_name: str = "mistralai/Mistral-7B-v0.1",
                 verbose_switch: bool = False,
                 quantization: str = "4bit",
                 use_cache: bool = True,
                 device_map: str = "auto",
                 max_new_tokens: int = 4096,
                 do_sample: bool = False,
                 top_p: float = 0.95,  # will be ignored if do_sample is False
                 top_k: int = 20,  # will be ignored if do_sample is False
                 temperature: float = 0.7,  # will be ignored if do_sample is False
                 llm_config_file: str = None,  # config file to easily set parameters
                 # stop strings to stop the generation, only used with the default chat template
                 stop_strings: List[str] = ["\n\nHuman:"],
                 # True: send messages, the pipeline applies the model's chat template
                 # False: send one flat string rendered with the default chat template                 
                 use_messages: bool = True,
                 enable_chat_history: bool = False,
                 max_history: int = 3,
                 seed: int = 42):
        """
        Creates a Huggingface LLM agent
        Args:
            model_name (str): The name of the HF repository, Default : mistral 7B v0.1
            quantization (str): The quantization method to use, 4bit or 8bit, Default : 4bit
            use_cache (bool): use the cached model when loading the model
            device_map (str): The device map to use for loading the model
            max_new_tokens (int): The maximum number of new tokens to generate
            do_sample (bool): Whether to use sampling when generating new tokens, 
                Default : False to make it deterministic
            top_p (float): The top-p value to use when sampling
            top_k (int): The top-k value to use when sampling, the number of highest probability vocabulary tokens 
                to keep for top-k-filtering.
            temperature (float): The temperature value to use when sampling
            llm_config_file (str): The path to a YAML file containing configuration values
            stop_strings (List[str]): Default : ["\\n\\nHuman:"] which supports the default chat template 
                at /config_files/default_chat_template.jinja, only used when that template is in use
            use_messages (bool): True to send messages (user/assistant turns) and let the pipeline apply 
                the model's chat template. False to send a flat string, rendered with the default chat template 
                (config_files/default_chat_template.jinja) even if the model has its own. 
                Models without a chat template always get the default one.
            enable_chat_history (bool): Whether to add chat history
            max_history (int): The maximum number of interactions to store in the chat
        """

        # base class
        super().__init__(model_name, enable_chat_history, max_history, verbose_switch)
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
        self.seed = seed
        self.stop_strings = stop_strings
        self.use_messages = use_messages

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
        self.has_chat_template = False
        self.default_template = None
        self.supports_system_role = True  # False: the system prompt is merged into the first user turn
        self.uses_default_template = True  # True: our template is used, needs stop strings
        self.generation_kwargs = {}  # extra kwargs for every pipeline call

        self._initialize_model()
        self._set_seed()


    def _set_seed(self):
        torch.manual_seed(self.seed)
        torch.cuda.manual_seed_all(self.seed)


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


    def _check_chat_template(self) -> bool:
        """
        Check if the tokenizer ships with a chat template.
        Returns:
            bool: True if a chat template is present
        """
        has_template = bool(getattr(self.tokenizer, "chat_template", None))
        if has_template:
            print_info(f"Chat template found for {self.model_name}")
        else:
            print_warning(f"No chat template found for {self.model_name}")
        return has_template


    def _set_fallback_chat_template(self):
        """
        Assign our own chat template to the tokenizer, for models that ship without one.
        """
        self.tokenizer.chat_template = self.default_template
        self.uses_default_template = True
        print_info("Default chat template assigned to the tokenizer")


    def _load_default_template(self) -> str:
        """
        Read the default chat template, config_files/default_chat_template.jinja
        """
        with open(self.prompt_template_path, "r") as template_file:
            return template_file.read()


    def _initialize_model(self):
        # quantization config
        quant_config = self._get_quant_config()

        # tokenizer
        self.tokenizer = self.set_tokenizer()  # don't add eos token for inference

        # set chat template, if the tokenizer doesn't ship with one, assign our own
        self._set_chat_template()

        # model
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=quant_config,
            use_cache=self.use_cache,
            device_map=self.device_map,
            dtype=torch.bfloat16
        )

        # pipeline
        self.pipeline = pipeline(
            model=self.model,
            tokenizer=self.tokenizer, # Check Type
            task="text-generation",
            do_sample=self.do_sample,
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
            repetition_penalty=1.1,
            return_full_text=False,
            max_new_tokens=self.max_new_tokens
        )

        print_success("Model initialized")  # DEBUG
        print_info(f"Model name: {self.model.name_or_path.strip().split('/')[-1]}")  # DEBUG


    def _set_chat_template(self):
        """
        Check if the tokenizer ships with a chat template, if not assign our own.
        If the model's template is used with messages, check that it accepts our messages, 
        otherwise fall back to our own template.
        """
        # Needed for flat strings and for models without a template
        self.default_template = self._load_default_template()
        self.has_chat_template = self._check_chat_template()
        self.uses_default_template = not self.has_chat_template or not self.use_messages
        if not self.has_chat_template:
            self._set_fallback_chat_template()

        # The model's template decides the roles it accepts
        if not self.uses_default_template:
            self.supports_system_role = self._check_system_role()
            if self.supports_system_role is None:
                print_warning(f"The chat template of {self.model_name} won't accept messages "
                              "even if the system prompt is merged into the first user turn.")
                print_warning(f"Using the default chat template instead")
                self._set_fallback_chat_template()
                self.supports_system_role = True
            elif not self.supports_system_role:
                print_warning(f"The chat template of {self.model_name} does not accept the system role, "
                              "the system prompt will be merged into the first user turn")

        if self.uses_default_template:
            # generate() needs the tokenizer to use stop strings
            self.generation_kwargs.update({"stop_strings": self.stop_strings, "tokenizer": self.tokenizer})


    def _check_system_role(self) -> Optional[bool]:
        """
        Render a sample conversation with the model's chat template, with and without a system message.
        Templates raise an error for roles they don't accept.
        Returns:
            Optional[bool]: True if the system role is accepted, False if the template only works without it,
                None if the template rejects the messages either way
        """
        system = [{"role": "system", "content": "system prompt"}]
        turns = [{"role": "user", "content": "question 1"},
                 {"role": "assistant", "content": "answer 1"},
                 {"role": "user", "content": "question 2"}]
        for with_system in (True, False):
            try:
                self.tokenizer.apply_chat_template((system if with_system else []) + turns,
                                                   tokenize=False,
                                                   add_generation_prompt=True)
                return with_system
            except TemplateError:
                continue
        return None


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

        # Messages first, it initialises the chat history if needed
        messages = self._prepare_messages(user_prompt, context, suppress_conversation_history)
        system_prompt = self._prepare_system_prompt(suppress_conversation_history)
        if self.supports_system_role:
            chat = [{"role": "system", "content": system_prompt}, *messages]
        else:
            # The first message is always a user turn, history is trimmed in whole pairs
            chat = [{"role": "user", "content": f"{system_prompt}\n\n{messages[0]['content']}"}, *messages[1:]]

        if self.use_messages:
            # the pipeline applies the chat template
            response = self.pipeline(chat, **self.generation_kwargs)
        else:
            # flat string, always rendered with our template, even if the model ships with its own
            prompt = self.tokenizer.apply_chat_template(chat,
                                                        chat_template=self.default_template,
                                                        tokenize=False,
                                                        add_generation_prompt=True)
            # the template already adds the bos token
            response = self.pipeline(prompt, add_special_tokens=False, **self.generation_kwargs)

        # Stop strings halt the generation but are still part of the output
        answer = response[0]["generated_text"]
        answer = self._remove_stop_strings(answer)

        if self.enable_chat_history:
            if not self.chat_history:
                self.init_chat_history(user_prompt)

            self.chat_history.add_interaction(user_prompt, answer)

        if self.verbose_switch:
            print_model_output(self.get_messages_as_string(system_prompt, messages)
                               if self.use_messages 
                               else prompt, "USER")
            
        _print_model_name = self.model.name_or_path.strip().split("/")[-1]
        print_model_output(answer + "\n", _print_model_name)
        return answer


    def _remove_stop_strings(self, text: str) -> str:
        """
        Remove stop strings from the generated text.
        
        Args:
            text (str): The generated text.
        
        Returns:
            str: The generated text without stop strings.
        """
        answer = text
        for stop_string in self.generation_kwargs.get("stop_strings", []):
            answer = answer.split(stop_string)[0]

        return answer.strip()


    def cleanup(self):
        """
        Clean up resources and release memory
        """
        # The pipeline and generation kwargs hold references to the model and tokenizer
        self.pipeline = None
        self.generation_kwargs = {}
        if self.model is not None:
            # self.model = self.model.to("cpu") # won't work for quantized models
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        torch.cuda.empty_cache()
        print_success("LLM resources cleaned up.")