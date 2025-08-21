# =================================================================================================
# PaperAnalyser.py - Research paper analysis and content extraction
# This module provides functionality to extract and analyse content from research papers
# including text extraction, section detection, figure processing, and LLM preprocessing.
#
# Usage:
#      analyser = PaperAnalyser("/path/to/paper.pdf")
#      text_content = analyser.extract_all_text()
# =================================================================================================

import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..'))

import pymupdf4llm
import fitz
import re
import json

from pathlib import Path
from typing import Dict, List, Optional, Union

from utils.output_message_format.output_colour import print_info, print_success, print_warning
from utils.output_message_format.output_colour import print_error
from utils.logger.Logger import Logger


class PaperAnalyser:
    """
    Research paper analysis and content extraction class.
    Handles text extraction, section detection, and content preprocessing for LLM consumption.
    """
    
    def __init__(self, 
                 pdf_path: Union[str, Path]) -> None:
        """
        Initialise the PaperAnalyser with a PDF file.
        
        Args:
            pdf_path: Path to the PDF file to analyse
        """
        self.pdf_path = Path(pdf_path)
        self.paper_json_path = self.pdf_path.with_suffix('.json')
        self.logger = Logger(self.__class__.__name__, "DEBUG")
        
        # Verify PDF exists
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")
            
        if not self.pdf_path.suffix.lower() == '.pdf':
            raise ValueError(f"File must be a PDF: {self.pdf_path}")
            
        # Analysis state
        self.raw_text: Optional[str] = None
        self.is_text_extracted = False
        self.sections: Dict[str, Dict] = {}
        self.is_sections_extracted = False
        
        self.logger.debug(f"Initialised PaperAnalyser object for: {self.pdf_path.name}")


    def extract_all_text(self) -> str:
        """
        Extract all text content from the PDF, similar to PDF upload processing.
        Preserves document structure and formatting for downstream analysis.
        
        Returns:
            Complete text content of the PDF
        """
        if self.is_text_extracted and self.raw_text:
            self.logger.debug("Text already extracted, returning cached result")
            return self.raw_text
            
        print_info(f"Extracting text from: {self.pdf_path.name}")
        
        try:
            # Primary method: pymupdf4llm (designed for LLM preprocessing)
            self.raw_text = self._extract_with_pymupdf4llm()
            
            self.is_text_extracted = True
            
            # Log extraction statistics
            char_count = len(self.raw_text)
            word_count = len(self.raw_text.split())
            print_success(f"Text extraction completed: {word_count:,} words, {char_count:,} characters")
            self.logger.debug(f"Extracted {word_count} words from {self.pdf_path.name}")
            
            return self.raw_text
            
        except Exception as e:
            print_error(f"Text extraction failed: {str(e)}")
            self.logger.error(f"Text extraction failed for {self.pdf_path.name}: {str(e)}")
            raise
        
        
    def extract_sections(self,
                         save_as_json: bool = False) -> Dict:
        """
        Extract sections from the PDF using regex pattern matching.

        Args:
            save_as_json (bool): Whether to save the extracted sections as a JSON file

        Returns:
            Dictionary with section names as keys and content dictionaries as values
        """
        if self.is_sections_extracted:
            self.logger.debug("Sections already extracted, returning cached result")
            return self.sections
            
        # Ensure text is extracted first
        if not self.is_text_extracted:
            self.extract_all_text()

        self.logger.debug(f"Extracting sections from: {self.pdf_path.name}")
        print_info(f"Extracting sections from: {self.pdf_path.name}")
        
        try:
            self.sections = self._extract_sections_with_regex()
            self.is_sections_extracted = True
            
            section_count = len(self.sections)
            section_names = list(self.sections.keys())
            
            log_message = f"Section extraction completed: {section_count} sections found"
            print_info(log_message)
            self.logger.debug(log_message)
            self.logger.debug(f"Extracted sections: {section_names}")

            if save_as_json:
                self._save_as_json(self.sections)

            return self.sections
            
        except Exception as e:
            print_error(f"Section extraction failed: {str(e)}")
            self.logger.error(f"Section extraction failed for {self.pdf_path.name}: {str(e)}")
            raise
        

    def get_extraction_summary(self) -> Dict:
        """
        Get summary of text extraction results.
        
        Returns:
            Dictionary with extraction statistics and metadata
        """
        if not self.is_text_extracted:
            return {
                'status': 'not_extracted',
                'pdf_path': str(self.pdf_path),
                'file_size_mb': self.pdf_path.stat().st_size / (1024 * 1024)
            }
            
        word_count = len(self.raw_text.split()) if self.raw_text else 0
        char_count = len(self.raw_text) if self.raw_text else 0
        
        return {
            'status': 'extracted',
            'pdf_path': str(self.pdf_path),
            'file_size_mb': self.pdf_path.stat().st_size / (1024 * 1024),
            'word_count': word_count,
            'character_count': char_count,
            'extraction_method': 'pymupdf4llm'
        }


    def _extract_with_pymupdf4llm(self) -> str:
        """
        Extract text using pymupdf4llm library (preferred method).
        This library is specifically designed for LLM preprocessing.
        
        Returns:
            Extracted text content
        """
        self.logger.debug("Using pymupdf4llm for text extraction")
        
        try:
            # pymupdf4llm.to_markdown() preserves structure and is LLM-friendly
            text_content: str = pymupdf4llm.to_markdown(str(self.pdf_path))
            
            if not text_content or len(text_content.strip()) == 0:
                raise ValueError("No text content extracted")
                
            return text_content
            
        except Exception as e:
            self.logger.error(f"pymupdf4llm extraction failed: {str(e)}")
            raise


    def _extract_with_pymupdf(self) -> str:
        """
        Extract text using PyMuPDF library (fallback method).
        
        Returns:
            Extracted text content
        """
        self.logger.debug("Using PyMuPDF for text extraction")
        
        try:
            doc = fitz.open(str(self.pdf_path))
            text_content = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                
                # Add page separator for multi-page documents
                if page_num > 0:
                    text_content += f"\n\n--- Page {page_num + 1} ---\n\n"
                    
                text_content += page_text
                
            doc.close()
            
            if not text_content or len(text_content.strip()) == 0:
                raise ValueError("No text content extracted")
                
            return text_content
            
        except Exception as e:
            self.logger.error(f"PyMuPDF extraction failed: {str(e)}")
            raise


    def _extract_sections_with_regex(self) -> Dict:
        """
        Extract sections using regex pattern matching on the text.
        
        Returns:
            Dictionary with section data
        """
        if not self.raw_text:
            raise ValueError("No text content available for section extraction")

        # Tested with pymupdf4llm extraction
        section_pattern = r'\n{3}\*\*([\d\.]*[A-Za-z\s\d]*)\*\*\n{3}'
        
        # Find all section headers with their positions
        matches = list(re.finditer(section_pattern, self.raw_text))
        
        if not matches:
            print_warning("No sections detected using regex pattern, creating fallback section")
            self.logger.warning(f"No regex matches found for pattern: {section_pattern}")
            return self._create_fallback_sections()
            
        self.logger.debug(f"Found {len(matches)} section headers using regex pattern: {section_pattern}")
        
        sections = {}
        
        for i, match in enumerate(matches):
            # Extract section name and clean it
            section_name = match.group(1).strip()
            
            if not section_name:
                self.logger.warning(f"Empty section name found at position {match.start()}")
                continue
            
            section_content = self._get_section_content(matches = matches, current_index = i)
            
            # Store section data
            sections[section_name] = {
                'text': section_content,
                'images': [],  # TODO: will contain extracted images' descriptions
                'tables': [],  # TODO: will contain extracted tables' descriptions
                'word_count': len(section_content.split()) if section_content else 0
            }
            
            self.logger.debug(f"Extracted section '{section_name}': {len(section_content)} characters")
            
        return sections
    
    
    def _get_section_content(self,
                             matches: list[re.Match],
                             current_index: int) -> str:
        """
        Extract content for a specific section.

        Args:
            matches (list[re.Match]): List of regex matches with section headers
            current_index (int): Index of the current section

        Returns:
            str: Extracted content for the current section
        """
        content_start = matches[current_index].end()
        if current_index + 1 < len(matches):
            content_end = matches[current_index + 1].start()
        else:
            content_end = len(self.raw_text)
            
        return self.raw_text[content_start:content_end].strip()


    def _create_fallback_sections(self) -> Dict:
        """
        Create fallback section when no sections are detected.
        
        Returns:
            Dictionary with single section containing all content
        """
        print_warning("No sections detected - creating single 'full_document' section")
        self.logger.warning("Fallback: creating single section with all content")
        
        return {
            'full_document': {
                'text': self.raw_text,
                'images': [],
                'tables': [],
                'word_count': len(self.raw_text.split()) if self.raw_text else 0
            }
        }
        
        
    def _save_as_json(self,
                      content: dict,
                      output_path: Union[str, Path] = None) -> None:
        """
        Save extracted content as JSON.

        Args:
            content (dict): Content to save
            output_path (Union[str, Path], optional): Path to save the JSON file. Defaults to None.
        """
        if output_path is None:
            output_path = self.paper_json_path

        with open(output_path, "w") as f:
            json.dump(content, f, indent=4)

        self.logger.info(f"Extracted sections saved to '{output_path}'")


if __name__ == "__main__":
    try:
        analyser = PaperAnalyser("services/Research/Paper/downloaded_papers/"
                                 "The Debugging Decay Index_ Rethinking Debugging St_40ba406a.pdf")
        analyser.extract_sections(save_as_json=True)
        
    except Exception as e:
        print_error(f"Analysis failed: {str(e)}")
        sys.exit(1)