# see https://python.langchain.com/v0.1/docs/modules/data_connection/document_transformers/recursive_text_splitter/
# see https://github.com/FullStackRetrieval-com/RetrievalTutorials/blob/main/tutorials/LevelsOfTextSplitting/5_Levels_Of_Text_Splitting.ipynb

import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from typing import List, Optional, Union
from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from tqdm.auto import tqdm

from Services.Embedding.Embedding import EmbeddingModel
from Services.Base import ServiceBase
from utils.output_message_format.output_colour import print_info, print_success

class VectorDatabase(ServiceBase):
    def __init__(self, 
                 embedding_model: EmbeddingModel, # can set this to default but then for every DB service it will crete a new model 
                 chunk_size: int = 1000, 
                 chunk_overlap: int = 100,
                 markdown_separators: List[str] = ["\n\n", "\n", ""], # hierarchy of the splitter strings
                 file_path: str = os.path.join(os.path.dirname(__file__), "documents/disqualified.txt") # for testing
                ):
        """
        Initialize the Vector Database
        Args:
            embedding_model (EmbeddingModel): The embedding model to use
            chunk_size (int): The size of the chunks to split the text into
            chunk_overlap (int): The overlap between the chunks
        """
        super().__init__()
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.vector_store = None # Will be FAISS object
        self.doc_path = file_path
        self.markdown_separators = markdown_separators
        self.text_splitter: RecursiveCharacterTextSplitter = self._initialize_text_splitter()

        # Loading and preparing the documents, ready to be queried
        self._load_and_prepare()


    def _initialize_text_splitter(self):
        return RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.markdown_separators


    def _load_documents(self, file_path: str) -> List:
        """
        Currently supports .pdf, .txt, and .csv files
        """
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == ".pdf":
            loader = PyPDFLoader(file_path)
        elif file_extension == ".txt":
            loader = TextLoader(file_path)
        elif file_extension == ".csv":
            loader = CSVLoader(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
            
        docs = loader.load()
        return self.text_splitter.split_documents(docs)


    def _initialize_vector_store(self, documents: List):
        """
        Will initialize FAISS vector store with the given documents
        """
        print_info("Initializing FAISS vector store...")
        self.vector_store = FAISS.from_documents(
            documents, 
            self.embedding_model.model, 
            distance_strategy=DistanceStrategy.COSINE
        )
        print_success("Vector store initialized.")


    def _load_and_prepare(self, file_path: str = None):
        if not file_path:
            file_path = self.doc_path

        print_info(f"Loading and processing documents from {file_path}...")
        documents = self._load_documents(file_path)
        self._initialize_vector_store(documents)


    def query(self, query: str, top_k: int = 3) -> List[str]:
        query_vector = self.embedding_model.embed_query(query)
        results = self.vector_store.similarity_search_by_vector(query_vector, top_k=top_k)
        return [result.page_content for result in results]
    

    def cleanup(self):
        """
        Clean up resources and release memory
        """
        if self.embedding_model is not None:
            self.embedding_model.cleanup()
            del self.embedding_model
            self.embedding_model = None
            
        if self.vector_store is not None:
            del self.vector_store
            self.vector_store = None
        print_success("VectorDatabase resources cleaned up.")
