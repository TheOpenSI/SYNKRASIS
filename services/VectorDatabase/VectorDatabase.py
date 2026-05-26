# ============================================================================================================================================
# see https://python.langchain.com/v0.1/docs/modules/data_connection/document_transformers/recursive_text_splitter/
# see https://github.com/FullStackRetrieval-com/RetrievalTutorials/blob/main/tutorials/LevelsOfTextSplitting/5_Levels_Of_Text_Splitting.ipynb
#
# Usage:
#   list_documents() -> List[str]
#   add_documents(file_paths: Union[str, Path, List[Union[str, Path]]) -> None
#   query(query: str, top_k: int = 3) -> List[dict]
# ============================================================================================================================================

import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import numpy as np

from typing import List, Optional, Union
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.documents import Document
from pathlib import Path

from services.Embedding.Embedding import EmbeddingModel
from services.Base import ServiceBase
from services.RAG.DocumentChunker import DocumentChunker
from utils.output_message_format.output_colour import print_info, print_success, print_warning
from services.DocumentProcessors.doc_data_models import Chunk

class VectorDatabase(ServiceBase):
    def __init__(self, 
                 embedding_model: EmbeddingModel, # can set this to default but then for every DB service it will crete a new model 
                 chunk_size: int = 1000, 
                 chunk_overlap: int = 200,
                 distance_strategy: DistanceStrategy = DistanceStrategy.COSINE
                ) -> None:
        """
        Initialise the Vector Database
        Args:
            embedding_model (EmbeddingModel): The embedding model to use
            chunk_size (int): The size of the chunks to split the text into
            chunk_overlap (int): The overlap between the chunks
        """
        super().__init__()
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.distance_strategy = distance_strategy
        
        self.vector_store: Optional[FAISS] = None
        self.document_chunker = DocumentChunker(chunk_size=self.chunk_size, 
                                                chunk_overlap=self.chunk_overlap)
        
        # document-level registry
        # key: document_name (str)
        # value: {"title": str, "chunk_count": int, "chunk_ids": List[str]}
        self.document_registry: dict[str, dict] = {}
        
        # chunk-level metadata store
        # key: UUID string assigned by LangChain on ingestion
        # value: full metadata dict mirroring Chunk fields
        self.chunk_metadata: dict[str, dict] = {}


    def _chunk_to_document(self, chunk: Chunk) -> Document:
        """
        Convert a Chunk object to a LangChain Document.
        The chunk text becomes page_content; all citation
        metadata fields are preserved in the metadata dict.
        
        Args:
            chunk (Chunk): The Chunk object to convert.
        
        Returns:
            Document: A LangChain Document with the chunk text and metadata.
        """
        return Document(
            page_content=chunk.text,
            metadata={
                "document_name":  chunk.document_name,
                "document_title": chunk.document_title,
                "chunk_index":    chunk.chunk_index,
                "chunk_method":   chunk.chunk_method,
                "page_start":     chunk.page_start,
                "page_end":       chunk.page_end,
                "heading_1":      chunk.heading_1,
                "heading_2":      chunk.heading_2,
                "heading_3":      chunk.heading_3,
            }
        )


    def _initialise_vector_store(self, documents: List[Document]) -> None:
        """
        Initialise FAISS vector store with the given documents.
        
        Args:
            documents (List[Document]): A list of documents to add to the vector store.
        """
        print_info("Initializing FAISS vector store...")
        self.vector_store = FAISS.from_documents(
            documents, 
            self.embedding_model.model, 
            distance_strategy=self.distance_strategy
        )
        print_success("Vector store initialised.")
        
        
    def _populate_chunk_metadata(self, 
                                 chunk_list: List[Chunk], 
                                 ids: List[str]) -> None:
        """
        Populate the chunk metadata store with the given documents and their corresponding IDs.
        
        Args:
            chunk_list (List[Chunk]): A list of chunks that were added to the vector store.
            ids (List[str]): A list of IDs corresponding to the chunks in the vector store.
        """
        for uid, chunk in zip(ids, chunk_list):
                self.chunk_metadata[uid] = {
                    "document_name":  chunk.document_name,
                    "document_title": chunk.document_title,
                    "chunk_index":    chunk.chunk_index,
                    "chunk_method":   chunk.chunk_method,
                    "page_start":     chunk.page_start,
                    "page_end":       chunk.page_end,
                    "heading_1":      chunk.heading_1,
                    "heading_2":      chunk.heading_2,
                    "heading_3":      chunk.heading_3
                }
       
                
    def _populate_document_registry(self,
                                    doc_name: str,
                                    chunk_list: List[Chunk],
                                    ids: List[str]) -> None:
        """
        Populate the document registry with the given document information.
        
        Args:
            doc_name (str): The name of the document.
            chunk_list (List[Chunk]): A list of chunks that were added to the vector store.
            ids (List[str]): A list of IDs corresponding to the chunks in the vector store.
        """
        self.document_registry[doc_name] = {
            "title":       chunk_list[0].document_title,
            "chunk_count": len(chunk_list),
            "chunk_ids":   ids
        }
        
    
    def _populate_registries(self,
                             doc_name: str,
                             chunk_list: List[Chunk],
                             ids: List[str]) -> None:
        """
        Populate both the chunk metadata store and the document registry with the given information.
        
        Args:
            doc_name (str): The name of the document.
            chunk_list (List[Chunk]): A list of chunks that were added to the vector store.
            ids (List[str]): A list of IDs corresponding to the chunks in the vector store.
        """
        self._populate_chunk_metadata(chunk_list, ids)
        self._populate_document_registry(doc_name, chunk_list, ids)
        
        
    def _check_if_document_exists(self,
                                  doc_name: str) -> bool:
        """
        Check if a document with the given name already exists in the document registry.
        
        Args:
            doc_name (str): The name of the document to check.
        
        Returns:
            bool: True if the document exists, False otherwise.
        """
        return doc_name in self.document_registry
    
    
    def _get_new_document_paths(self,
                                file_paths: List[Union[str, Path]]) -> List[Union[str, Path]]:
        """
        Given a list of file paths, return a list of paths that do not correspond to documents already in the registry.
        
        Args:
            file_paths (List[Union[str, Path]]): A list of file paths to check.
        
        Returns:
            List[Union[str, Path]]: A list of file paths that are not already in the document registry.
        """
        new_paths = []
        for path in file_paths:
            doc_name = Path(path).name
            if self._check_if_document_exists(doc_name):
                print_info(f"Skipping {doc_name} — already in vector store.")
            else:
                new_paths.append(path)
        return new_paths
    
    
    def list_documents(self) -> List[str]:
        """
        Return the names of all documents currently in the vector store.
        """
        return list(self.document_registry.keys())


    def add_documents(
        self,
        file_paths: Union[str, Path, List[Union[str, Path]]]) -> None:
        """
        Chunk and add one or more PDF documents to the vector store.
        Documents already present in the registry are skipped.
        Args:
            file_paths: A single file path or list of file paths to PDF files.
        """
        # normalise to list
        if isinstance(file_paths, (str, Path)):
            file_paths = [file_paths]

        # get paths of new documents
        new_paths = self._get_new_document_paths(file_paths)

        if not new_paths:
            print_info("No new documents to add.")
            return

        # chunk all new documents — returns list[list[Chunk]]
        print_info(f"Chunking {len(new_paths)} document(s)...")
        all_chunk_lists: list[list[Chunk]] = self.document_chunker.chunk_documents(new_paths)

        # process each document's chunks
        for path, chunk_list in zip(new_paths, all_chunk_lists):
            doc_name = Path(path).name

            if not chunk_list:
                print_warning(f"No chunks produced for {doc_name}, skipping.")
                continue

            documents = [self._chunk_to_document(chunk) for chunk in chunk_list]

            # initialise or append
            if self.vector_store is None:
                self._initialise_vector_store(documents)
                
                # LangChain does not return IDs from from_documents,
                # so we read them from the docstore directly
                ids = list(self.vector_store.index_to_docstore_id.values())
            else:
                ids = self.vector_store.add_documents(documents)

            # populate chunk_metadata and document registry
            self._populate_registries(doc_name, chunk_list, ids)

            print_success(f"Added {len(chunk_list)} chunks from {doc_name}.")


    def query(self, query: str, top_k: int = 3) -> List[dict]:
        """
        Query the vector store with the given query and return the top K most relevant chunks along with their metadata.

        Args:
            query (str): The query string to search for in the vector store.
            top_k (int, optional): The number of top relevant chunks to return. Defaults to 3.

        Raises:
            RuntimeError: If the vector store is empty or not initialised.

        Returns:
            List[dict]: A list of dictionaries, each containing the text of a relevant chunk, its relevance score, and associated metadata.
        """
        if self.vector_store is None:
            raise RuntimeError("Vector store is empty. Add documents before querying.")

        query_vector = self.embedding_model.embed_query(query)
        
        # raw FAISS search returns (distances, integer indices) as numpy arrays
        distances, indices = self.vector_store.index.search(
            np.array([query_vector], dtype=np.float32), top_k
        )

        output = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
            uid = self.vector_store.index_to_docstore_id[idx]
            meta = self.chunk_metadata[uid]
            doc = self.vector_store.docstore.search(uid)
            output.append({
                "text":  doc.page_content,
                "score": float(dist),
                **meta
            })

        return output
    

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
