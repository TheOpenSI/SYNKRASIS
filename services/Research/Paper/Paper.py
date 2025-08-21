from __future__ import annotations
import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..'))

# =================================================================================================
# Paper.py - Research paper analysis and preprocessing class
# This module provides functionality to download research papers and prepare them for LLM analysis
# with section detection, figure extraction, and table processing.
#
# Usage:
#      # From GScholar metadata
#      paper = Paper(paper_metadata_dict)
#      paper.download_and_analyse()
#      
#      # From existing PDF file
#      paper = Paper.from_pdf_file("/path/to/paper.pdf")
#      paper.analyse()
# =================================================================================================

import os
import sys
import requests
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from utils.output_message_format.output_colour import print_info, print_success, print_warning
from utils.output_message_format.output_colour import print_error
from utils.logger.Logger import Logger
from services.Research.Paper.PaperAnalyser import PaperAnalyser


@dataclass
class PaperMetadata:
    """Structured metadata for research papers."""
    title: str
    authors: List[str]
    year: str
    venue: str
    abstract: str
    pub_url: str
    pdf_url: str
    pdf_source: str
    pdf_confidence: float
    citations: int


class Paper:
    """
    Research paper analysis and preprocessing class for LLM consumption.
    Handles downloading, section detection, and content extraction.
    """
    
    def __init__(self, 
                 paper_metadata: Union[Dict, PaperMetadata],
                 download_dir: str = 
                    os.path.dirname(os.path.abspath(__file__)) + "/downloaded_papers/",
                 analysis_dir: str = 
                    os.path.dirname(os.path.abspath(__file__)) + "/analysed_papers/") -> None:
        """
        Initialise the Paper class with metadata from GScholar.
        
        Args:
            paper_metadata: Paper metadata from GScholar search results
            download_dir: Directory to store downloaded PDF files
            analysis_dir: Directory to store analysis results
        """
        if isinstance(paper_metadata, dict):
            self.metadata = PaperMetadata(**paper_metadata)
        else:
            self.metadata = paper_metadata
            
        self.download_dir = Path(download_dir)
        self.analysis_dir = Path(analysis_dir)
        self.logger = Logger(self.__class__.__name__, "DEBUG")
        
        # Create directories
        self.download_dir.mkdir(exist_ok=True)
        self.analysis_dir.mkdir(exist_ok=True)
        
        # Internal state
        self.pdf_path: Optional[Path] = None
        self.is_downloaded = False
        self.is_analysed = False
        self.analysis_results: Optional[Dict] = None
        self.paper_analyser = None
        
        self.logger.debug(f"Initialised Paper object for: {self.metadata.title[:50]}...")


    @classmethod
    def from_pdf_file(cls, 
                      pdf_path: str,
                      analysis_dir: str = "./analysed_papers/") -> Paper:
        """
        Create Paper instance from existing PDF file.
        
        Args:
            pdf_path: Path to existing PDF file
            analysis_dir: Directory to store analysis results
            
        Returns:
            Paper instance ready for analysis
        """
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
        metadata = PaperMetadata(
            title=pdf_file.stem,  # Use filename as title
            authors=[],
            year="Unknown",
            venue="Unknown", 
            abstract="Not available - loaded from file",
            pub_url="",
            pdf_url="",
            pdf_source="local_file",
            pdf_confidence=1.0,
            citations=0
        )
        
        # Create instance
        paper = cls(metadata, analysis_dir=analysis_dir)
        paper.pdf_path = pdf_file
        paper.is_downloaded = True
        
        print_info(f"Loaded paper from file: {pdf_file.name}")
        paper.logger.debug(f"Loaded paper from file: {pdf_file.name}")
        return paper


    def download_and_analyse(self) -> Dict:
        """
        Download PDF and perform full analysis pipeline.
        
        Returns:
            Dictionary containing analysis results
        """
        self.download()
        return self.analyse()


    def download(self) -> bool:
        """
        Download the PDF file from the URL in metadata.
        
        Returns:
            True if download successful, False otherwise
        """
        if not self.metadata.pdf_url:
            print_error("No PDF URL available for download")
            self.logger.error(f"No PDF URL for paper: {self.metadata.title[:50]}")
            return False
            
        if self.is_downloaded and self.pdf_path and self.pdf_path.exists():
            print_info("PDF already downloaded")
            return True
            
        try:
            # Generate filename from title hash to avoid filesystem issues
            title_hash = hashlib.md5(self.metadata.title.encode()).hexdigest()[:8]
            safe_title = self._sanitise_filename(self.metadata.title[:50])
            filename = f"{safe_title}_{title_hash}.pdf"
            self.pdf_path = self.download_dir / filename
            
            print_info(f"Downloading PDF: {self.metadata.title[:50]}...")
            self.logger.debug(f"Downloading from URL: {self.metadata.pdf_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(self.metadata.pdf_url, 
                                  headers=headers, 
                                  stream=True, 
                                  timeout=30)
            response.raise_for_status()
            
            # Write file
            with open(self.pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            self.is_downloaded = True
            file_size = self.pdf_path.stat().st_size / (1024 * 1024)  # MB
            print_success(f"Downloaded successfully: {file_size:.1f} MB")
            self.logger.debug(f"Downloaded to: {self.pdf_path}")
            
            # Paper Analyser
            self.paper_analyser = PaperAnalyser(pdf_path=self.pdf_path, 
                                                output_path=self.analysis_dir,
                                                paper_title=safe_title)
            self.logger.debug(f"Initialised PaperAnalyser for: {self.pdf_path.name}")
            
            return True
            
        except requests.RequestException as e:
            print_error(f"Download failed: {str(e)}")
            self.logger.error(f"Download failed for {self.metadata.title[:50]}: {str(e)}")
            return False
        except Exception as e:
            print_error(f"Unexpected error during download: {str(e)}")
            self.logger.error(f"Unexpected download error: {str(e)}")
            return False


    def analyse(self) -> Dict:
        """
        Perform complete paper analysis pipeline.
        
        Returns:
            Dictionary containing all analysis results
        """
        if not self.is_downloaded or not self.pdf_path or not self.pdf_path.exists():
            raise ValueError("PDF must be downloaded before analysis")
            
        log_message = f"Starting analysis of: {self.metadata.title[:50]}..."
        print_info(log_message)
        self.logger.debug(log_message)
        
        text = self.paper_analyser.extract_all_text()
        sections = self.paper_analyser.extract_sections(save_as_json = False)
        
        self.analysis_results = {
            'status': 'placeholder',
            'pdf_path': str(self.pdf_path),
            'title': self.metadata.title,
            'sections': [],
            'figures': [],
            'tables': [],
            'processed_content': ""
        }
        
        self.is_analysed = True
        print_success("Analysis completed (placeholder)")
        
        return self.analysis_results


    def _sanitise_filename(self, filename: str) -> str:
        """
        Sanitise filename by removing invalid characters.
        
        Args:
            filename: Original filename string
            
        Returns:
            Sanitised filename safe for filesystem
        """
        # Remove invalid characters for filesystems
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
            
        # Replace multiple underscores with single
        while '__' in filename:
            filename = filename.replace('__', '_')
            
        return filename.strip('_')


if __name__ == "__main__":
    sample_metadata = {
        'title': 'The Debugging Decay Index: Rethinking Debugging Strategies for Code LLMs',
        'authors': ['Author One', 'Author Two'],
        'year': '2024',
        'venue': 'Conference Name',
        'abstract': 'This is a sample abstract...',
        'pub_url': 'https://example.com/paper',
        'pdf_url': 'https://arxiv.org/pdf/2506.18403',
        'pdf_source': 'arxiv_discovery',
        'pdf_confidence': 0.95,
        'citations': 10
    }
    
    paper = Paper(sample_metadata)
    paper.download()