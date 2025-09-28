import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")

import fitz  # PyMuPDF
import pymupdf4llm

from typing import Union, Dict
from pathlib import Path
from utils.logger.Logger import Logger

class ContentExtractor:
    def __init__(self):
        """
        Document content extractor.
        """
        self.logger = Logger(self.__class__.__name__, "DEBUG")
        self.supported_formats = {'.pdf'}
        self.logger.info("Document Content Extractor initialised.")
        
        
    def extract_with_pymullm(self, 
                             file_path: Union[str, Path]) -> Dict:
        """
        Extract text content from document using pymupdf4llm.
        Keeps content structure (headings, lists, etc.)
        Suitable for LLM input.
        Not suitable for very large documents.
        
        Args:
            file_path: Path to the document file

        Returns:
            dict: Dict with extracted content and metadata
                {
                    'file_path': str,
                    'file_name': str,
                    'content': str,
                    'success': bool,
                    'error': Optional[str]
                }
        """
        self.logger.info(f"Extracting content from {file_path} using pymupdf4llm.")
        file_path = Path(file_path)
        is_suitable_for_extraction = self._check_if_suitable_for_extraction(file_path)
        
        if is_suitable_for_extraction:
            content = pymupdf4llm.to_markdown(str(file_path))
            self.logger.info(f"Extraction successful from {file_path} using pymupdf4llm.")

            return {
                'file_path': str(file_path),
                'file_name': file_path.name,
                'content': content,
                'success': True,
                'error': None
            }
        self.logger.error(f"Extraction failed from {file_path} using pymupdf4llm.")
            
            
    def extract_with_fitz(self,
                          file_path: Union[str, Path]) -> Dict:
        """
        Extract text content from PDF using PyMuPDF (fitz).
        Suitable for large documents but does not preserve structure.
        
        Args:
            file_path: Path to the PDF file

        Returns:
            dict: Dict with extracted content and metadata
                {
                    'file_path': str,
                    'file_name': str,
                    'content': str,
                    'success': bool,
                    'error': Optional[str]
                }
        """
        file_path = Path(file_path)
        self.logger.info(f"Extracting content from {file_path} using fitz.")
        is_suitable_for_extraction = self._check_if_suitable_for_extraction(file_path)
        
        if is_suitable_for_extraction:
            doc = fitz.open(file_path)
            full_text = ""
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                full_text += page.get_text()
            
            doc.close()
            self.logger.info(f"Extraction successful from {file_path} using fitz.")
            
            return {
                'file_path': str(file_path),
                'file_name': Path(file_path).name,
                'content': full_text,
                'success': True,
                'error': None
            }

        self.logger.error(f"Extraction failed from {file_path} using fitz.")
        
        
    def _check_if_suitable_for_extraction(self,
                                          file_path: Path) -> bool:
        """
        Check if the file exists and format is supported for extraction.
        
        Args:
            file_path: Path to the document file

        Returns:
            bool: True if the file is suitable for extraction, False otherwise
        """
        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
            
        if file_path.suffix.lower() not in self.supported_formats:
            self.logger.error(f"Unsupported format: {file_path.suffix}")
            raise ValueError(f"Unsupported format: {file_path.suffix}")

        return True