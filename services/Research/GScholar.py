# https://pypi.org/project/duckduckgo-search/
# https://pypi.org/project/scholarly/
# https://scholarly.readthedocs.io/en/latest/?badge=latest

import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import requests
import re
import time
from scholarly import scholarly

from utils.output_message_format.output_colour import print_info, print_success, print_warning
from utils.output_message_format.output_colour import print_error

class GScholar:
    """
    Google Scholar research agent with arXiv PDF discovery.
    """
    
    def __init__(self, 
                 max_results: int = 5,
                 base_delay: float = 2.0) -> None:
        """
        Initialise the GScholar agent.
        
        Args:
            max_results: Maximum number of results to return
            base_delay: Delay between requests to avoid rate limiting
        """
        self.max_results = max_results
        self.base_delay = base_delay
    
    
    def _visit_publication_page(self, pub_url: str) -> str:
        """
        Visit the publication page to extract information.
        
        Args:
            pub_url: The publication URL from Google Scholar
        
        Returns:
            str: Raw HTML content of the publication page
            
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                              'AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(pub_url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print_error(f"Network error while visiting publication page: {e}")
            raise e
        
        
    def _check_for_arxiv_link(self, raw_html: str) -> list:
        """
        Check the raw HTML for arXiv links.
        
        Args:
            raw_html: The raw HTML content of the publication page
        
        Returns:
            list: List of dictionaries with arXiv PDF links and metadata
        """
        arxiv_pattern = r'(?:https?://)?arxiv\.org/(pdf|abs)/([0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?)'
        matches = re.findall(arxiv_pattern, raw_html, re.IGNORECASE)
        
        arxiv_links = [] # should be one
        
        for match in matches:
            path_type = match[0]  # 'pdf' or 'abs'
            paper_id = match[1]   # The paper ID like '2024.12345'
            pdf_url = f"https://arxiv.org/pdf/{paper_id}"
            
            # Store information about what we found
            link_info = {
                'pdf_url': pdf_url,
                'paper_id': paper_id,
                'original_type': path_type,  # Was this originally a PDF or abstract link?
                'confidence': 0.95 if path_type == 'pdf' else 0.90,
                'regex_match': match,
            }
            
            arxiv_links.append(link_info)
            print(f"Found arXiv {path_type} link for paper {paper_id}")
        
        return sorted(arxiv_links, key=lambda x: x['confidence'], reverse=True)
    
    
    def _validate_arxiv_pdf_link(self, arxiv_url_links: list) -> str:
        """
        Validate if the arXiv PDF link is accessible.
        
        Args:
            arxiv_url_links: List of dictionaries with arXiv PDF links and metadata
        
        Returns:
            str: The validated arXiv PDF link if accessible, otherwise an empty string
        """
        try:
            for arxiv_link in arxiv_url_links:
                arxiv_url = arxiv_link['pdf_url']
                # NOTE: print(f"Validating arXiv PDF link: {arxiv_url}")
                head_response = requests.head(arxiv_url, timeout=5)
                
                if head_response.status_code == 200:
                    print_success(f"Confirmed arXiv PDF is accessible")
                    return arxiv_url
                # else:
                    # NOTE: print(f"ArXiv PDF link: {arxiv_url} "
                    #       f"returned status code: {head_response.status_code}")
                
        except requests.RequestException:
            print_warning(f"Could not validate arXiv PDF accessibility")
            return ""


    def _check_publication_page(self, pub_url: str):
        """
        Check the publication page for arXiv links.

        Args:
            pub_url (str): The URL of the publication page

        Returns:
            str: The validated arXiv PDF link, if found and accessible
        """
        raw_html = self._visit_publication_page(pub_url)
        links = self._check_for_arxiv_link(raw_html)
        if len(links) > 0:
            validated_link = self._validate_arxiv_pdf_link(links)
           
            if validated_link == "":
                print_warning(f"Could not validate any arXiv links from publication page")
                return ""
            
            else:
                print_success(f"Validated arXiv PDF link: {validated_link}")
                return validated_link
            
        else:
            print("No arXiv links found in publication page")
            return ""


    def paper_search(self, 
                    query: str) -> list:
        """
        Search for papers on Google Scholar.
        
        Args:
            keyword: Search keyword or phrase
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries with paper information, including PDF URLs if found
        """
        print_info(f"Searching Google Scholar for: {query} (max {self.max_results} results)")
        papers = []
        
        # Generator, sort by date to get abstracts
        search_query = scholarly.search_pubs(query=query,
                                             sort_by="date")
        
        for i in range(self.max_results):
            try:
                paper = next(search_query)
                paper_info = {
                    'title': paper.get('bib', {}).get('title', 'Title not available'),
                    'authors': paper.get('bib', {}).get('author', []),
                    'year': paper.get('bib', {}).get('pub_year', 'Year unknown'),
                    'venue': paper.get('bib', {}).get('venue', 'Venue unknown'),
                    'abstract': paper.get('bib', {}).get('abstract', 'No abstract available'),
                    'pub_url': paper.get('pub_url', ''),
                    'pdf_url': paper.get('eprint_url', ''),  # Direct PDF from Scholar
                    'citations': paper.get('num_citations', 0)
                }
                
                # Check if we have a direct PDF link from Google Scholar
                if paper_info['pdf_url']:
                    paper_info['pdf_source'] = 'google_scholar_direct'
                    paper_info['pdf_confidence'] = 1.0
                    print_info(f"Direct PDF available from Google Scholar for "
                               f"{paper_info['title'][:40]}...")
                    
                elif paper_info['pub_url']:
                    print_info(f"No direct PDF, searching for arXiv link from the publication URL...")
                    fetched_arxiv_link = self._check_publication_page(pub_url=paper_info['pub_url'])
                    
                    paper_info['pdf_url'] = fetched_arxiv_link
                    paper_info['pdf_source'] = 'arxiv_discovery' \
                                               if fetched_arxiv_link \
                                               else None
                    paper_info['pdf_confidence'] = 1.0 if fetched_arxiv_link else 0
                    
                    if fetched_arxiv_link:
                        print_success(f"Found arXiv PDF link for {paper_info['title'][:40]}...")
                    else:
                        print_warning(f"No arXiv PDF link found for {paper_info['title'][:40]}...")
                else:
                    paper_info['pdf_source'] = ''
                    paper_info['pdf_url'] = ''
                    paper_info['pdf_confidence'] = -1 # No publiction
                    print_warning(f"No publication URL available for {paper_info['title'][:40]}...")
                    
                
                papers.append(paper_info)
                
                # Progress indicator
                pdf_status = "✓ PDF found" if paper_info['pdf_url'] else "✗ No PDF"
                print(f"Paper {i+1}: {pdf_status} - {paper_info['title'][:40]}...")
                
                if i < self.max_results - 1:
                    time.sleep(self.base_delay)
                    
            except StopIteration:
                print_info(f"Search completed - found {len(papers)} papers")
                break
        
        return papers
    
    
if __name__ == "__main__":
    gscholar = GScholar(max_results=5, base_delay=2.0)
    results = gscholar.paper_search("code vulnerability for LLM generated code")

    for paper in results:
        print(paper)