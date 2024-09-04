# The default models from thenlper are not gated
# I may add huggingface login to the base class if needed

import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from langchain_huggingface import HuggingFaceEmbeddings
from typing import List

from utils.output_message_format.output_colour import print_info, print_success
from Services.Base import ServiceBase


class EmbeddingModel(ServiceBase):
    def __init__(self, 
                 model_name: str = "thenlper/gte-small", 
                 device: str = "cuda", 
                 multi_process: bool = True):
        super().__init__()
        self.model_name = model_name
        self.device = device
        self.multi_process = multi_process
        self.model = self._initialize_model()

    def _initialize_model(self):
        return HuggingFaceEmbeddings(
            model_name=self.model_name,
            multi_process=self.multi_process,
            model_kwargs={"device": self.device},
            encode_kwargs={"normalize_embeddings": True},  # for cosine similarity
        )


    def embed_documents(self, documents: List[str]) -> List[float]:
        return self.model.embed_documents(documents)


    def embed_query(self, query: str) -> List[float]:
        return self.model.embed_query(query)


    def cleanup(self):
        """
        Clean up resources and release memory
        """
        print_info("Cleaning up EmbeddingModel resources...")
        if self.model is not None:
            del self.model
            self.model = None
        print_success("EmbeddingModel resources cleaned up.")


    def __del__(self):
        """
        Destructor to ensure cleanup is called
        """
        self.cleanup()
 
# ===================================================================================================
# if __name__ == '__main__':
#     emb = EmbeddingModel()
#     print(emb.model.__config__)