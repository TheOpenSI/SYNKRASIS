# ===================================================================================================================================
# Uses Llama3.2-vision model for OCR.
# Tested with .png and .jpg images.
# Methods:
#   - generate_response(image_path: str) -> Optional[str]: Generate OCR response.
# ===================================================================================================================================
import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from io import BytesIO
from PIL import Image
from typing import Optional

from services.Base import ServiceBase
from services.LLM.Ollama.Ollama import Ollama

class OCR(ServiceBase):
    def __init__(self):
        """
        Uses Llama3.2-vision model for OCR.
        """
        super().__init__()
        self.MODEL_NAME = "llama3.2-vision"
        self.USER_PROMPT = ("Analyze the text in the provided image. Extract all readable content \n"
                    "and present it in a structured Markdown format that is clear, concise\n"
                    " and well-organized. Ensure proper formatting (e.g., headings, lists,\n"
                    " or code blocks) as necessary to represent the content effectively.")
        self.model = Ollama(model_name = self.MODEL_NAME, 
                            enable_chat_history = False,
                            max_history = 0)
        self.model.set_system_prompt("") # NOTE: https://github.com/patchy631/ai-engineering-hub/blob/main/llama-ocr/app.py
        
        
    def generate_response(self, image_path: str) -> Optional[str]:
        """
        Generate OCR response.

        Args:
            image_path (str): Path to the image file.

        Returns:
            str: OCR response.
        """
        # NOTE: https://www.geeksforgeeks.org/python-pil-image-open-method/
        image = Image.open(image_path)
        image_binary = BytesIO()
        image.save(image_binary, format = image.format)
        image_binary_data = image_binary.getvalue()
        return self.model.chat(
            user_prompt = self.USER_PROMPT,
            messages = [{
                "role": "user",
                "content": self.USER_PROMPT,
                "images": [image_binary_data]
            }],
        )
        
    def cleanup(self):
        self.model.cleanup()