# =============================================================================================
# Collects all data from the MITRE CWE REST API for analysis
# Hits all available endpoints for a given CWE ID
# Saves raw and processed data to files for further analysis
# =============================================================================================
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
import requests
import json
import time

from typing import Dict, Any, Optional, Union
from datetime import datetime
from tqdm import tqdm

from utils.logger.Logger import Logger
from utils.output_message_format.output_colour import print_info, print_success, \
    print_warning, print_error

class CWEAPIAnalysis:
    def __init__(self, 
                 base_url: str = "https://cwe-api.mitre.org/api/v1",
                 analysis_dir: str = \
                     "/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/cwe_analysis/analysis"
                ) -> None:
        self.logger = Logger(self.__class__.__name__, "DEBUG")
        self.base_url = base_url
        self.request_delay = 1.0
        self.analysis_dir = analysis_dir
        
        os.makedirs(self.analysis_dir, exist_ok=True)
        
        
    def _analyse_endpoint(self, 
                         endpoint: str) -> dict: 
        """
        Collect data from the given endpoint.
        
        Args:
            endpoint (str): The API endpoint to test (e.g. "/cwe/version")
            
        Returns:
            dict: Parsed JSON response if successful, None otherwise.
        """
        url = f"{self.base_url}{endpoint}" # endpoints lead with /
        self.logger.debug(f"Testing endpoint: {endpoint}")
        print_info(f"Testing endopoint: {endpoint}")
        
        try:
            response = requests.get(url, timeout=30)
        
            self.logger.debug(f"Status Code: {response.status_code}")
            self.logger.debug(f"Response Time: {response.elapsed.total_seconds():.2f}s")
            self.logger.debug(f"Content Type: {response.headers.get('content-type', 'Unknown')}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    self.logger.debug(f"Response Size: {len(json.dumps(data))} characters")
                    
                    return {
                        'endpoint': endpoint,
                        'url': url,
                        'status_code': response.status_code,
                        'success': True,
                        'error': None,
                        'data': data
                    }
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON decode error: {e}")
                    self.logger.error(f"Raw response: {response.text[:500]}...")
                    return {
                        'endpoint': endpoint,
                        'url': url,
                        'status_code': response.status_code,
                        'success': False,
                        'error': f"JSON decode error: {e}",
                        'data': response.text
                    }
            else:
                self.logger.error(f"Error: HTTP {response.status_code}")
                self.logger.error(f"Response: {response.text[:200]}...")
                return {
                    'endpoint': endpoint,
                    'url': url,
                    'status_code': response.status_code,
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text[:200]}",
                    'data': None
                }
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error: {e}")
            return {
                'endpoint': endpoint,
                'url': url,
                'status_code': None,
                'success': False,
                'error': f"Request error: {e}",
                'data': None
            }
        
        finally:
            self.logger.debug(f"Waiting {self.request_delay}s before next request...")
            time.sleep(self.request_delay)
    
    
    def _process_endpoint_id(self, result: list) -> dict:
        """
        Checks if the result belongs to a valid/current CWE.
        
        Args:
            result (list): The API response - list containing one dict
            
        Returns:
            dict: Processed result with 'is_deprecated' field
        """
        self.logger.debug("Processing /cwe/id endpoint result")
        
        if not result or len(result) == 0:
            self.logger.warning("Empty result from /cwe/id endpoint")
            return None
        
        cwe_data = result[0]
        is_deprecated = "deprecated" in cwe_data.get("Type", "").lower()
        
        processed = {
            'ID': cwe_data.get('ID'),
            'Type': cwe_data.get('Type'),
            'is_deprecated': is_deprecated
        }
        
        self.logger.debug(f"Processed result: ID={processed['ID']}, deprecated={is_deprecated}")
        return processed
                
    
    def _process_endpoint_weakness(self,
                                   weakness_response: dict) -> dict:
        """
        Extracts relevant fields from the /cwe/weakness/{id} endpoint response
        to create a clean node representation for the knowledge graph.
        
        Args:
            weakness_response: Dict containing the full API response
            
        Returns:
            Dict with extracted fields for graph node
        """
        self.logger.debug(f"Processing /cwe/weakness/id endpoint result")
        weaknesses = weakness_response.get("Weaknesses", [])
        
        if not weaknesses:
            self.logger.warning("No weaknesses found in response")
            return None

        # Take first weakness (should only be one when querying by ID)
        if len(weaknesses) > 1:
            print_warning("Multiple weaknesses found in response; using the first one.")
        weakness = weaknesses[0]
        
        node_data = {
            "ID": weakness.get("ID", None),
            "Name": weakness.get("Name", None),
            "Abstraction": weakness.get("Abstraction", None),
            "Structure": weakness.get("Structure", None),
            "Status": weakness.get("Status", None),
            "Description": weakness.get("Description", None),
            "ExtendedDescription": weakness.get("ExtendedDescription", None),
            "LikelihoodOfExploit": weakness.get("LikelihoodOfExploit", None),
            "ApplicablePlatforms": weakness.get("ApplicablePlatforms", None),
            "AlternateTerms": weakness.get("AlternateTerms", None),
            "ModesOfIntroduction": weakness.get("ModesOfIntroduction", None),
            "CommonConsequences": weakness.get("CommonConsequences", None),
            "DemonstrativeExamples": weakness.get("DemonstrativeExamples", None),
            "PotentialMitigations": weakness.get("PotentialMitigations", None)
        }
        
        return node_data
    
    
    def _process_endpoint_parents(self,
                                  parents: list) -> dict:
        """
        Extracts parent relationships, filtering out views.
        
        Returns:
            dict with two keys:
                - 'weakness_parents': list of IDs for class_weakness type
                - 'category_parents': list of IDs for category type
        """
        self.logger.debug("Processing /cwe/id/parents endpoint result")
        weakness_parents = []
        category_parents = []
        
        # Track seen IDs to avoid duplicates (ignoring ViewID)
        seen_weaknesses = set()
        seen_categories = set()
        
        for parent in parents:
            parent_id = parent.get("ID")
            parent_type = parent.get("Type")
            
            if parent_type == "class_weakness":
                if parent_id not in seen_weaknesses:
                    weakness_parents.append(parent_id)
                    seen_weaknesses.add(parent_id)
                    
            elif parent_type == "category":
                if parent_id not in seen_categories:
                    category_parents.append(parent_id)
                    seen_categories.add(parent_id)
            
        self.logger.debug((f"Found {len(weakness_parents)} weakness parents "
                           f"and {len(category_parents)} category parents"))
        return {
            'weakness_parents': weakness_parents,
            'category_parents': category_parents
        }
        
        
    def _process_endpoint_child(self, 
                                    children_response: list) -> dict:
        """
        Extracts child relationships, filtering out views.
        
        Returns:
            dict with two keys:
                - 'weakness_children': list of IDs for weakness types
                - 'category_children': list of IDs for category type
        """
        self.logger.debug("Processing /cwe/id/children endpoint result")
        children = children_response  # Assuming this is the list
        
        weakness_children = []
        category_children = []
        
        seen_weaknesses = set()
        seen_categories = set()
        
        # Weakness types to include
        weakness_types = {'variant_weakness', 'base_weakness', 'class_weakness', 'compound_weakness'}
        
        for child in children:
            child_id = child.get("ID")
            child_type = child.get("Type")
            
            if child_type in weakness_types:
                if child_id not in seen_weaknesses:
                    weakness_children.append(child_id)
                    seen_weaknesses.add(child_id)
                    
            elif child_type == "category":
                if child_id not in seen_categories:
                    category_children.append(child_id)
                    seen_categories.add(child_id)
            
            # Ignore child_type == "view"
        
        self.logger.debug((f"Found {len(weakness_children)} weakness children "
                           f"and {len(category_children)} category children"))
        return {
            'weakness_children': weakness_children,
            'category_children': category_children
        }
        
        
    def _get_endpoints(self,
                       cwe_id: Union[str, int]) -> list[tuple[str, callable]]:
        """
        Returns a list of endpoints from the API.
        https://github.com/CWE-CAPEC/REST-API-wg/blob/main/Quick%20Start.md
        """
        return [
            (f"/cwe/{cwe_id}", self._process_endpoint_id),
            (f"/cwe/weakness/{cwe_id}", self._process_endpoint_weakness),
            (f"/cwe/{cwe_id}/parents", self._process_endpoint_parents),
            (f"/cwe/{cwe_id}/children", self._process_endpoint_child)
        ]     
    
    
    def _save_results(self, 
                     cwe_id: Union[str, int],
                     raw: dict,
                     processed: dict) -> None:
        """
        Save all results to file for analysis
        
        Args:
            cwe_id (Union[str, int]): The CWE ID being tested.
        """
        cwe_dir = os.path.join(self.analysis_dir, f"CWE-{cwe_id}")
        os.makedirs(cwe_dir, exist_ok=True)
        raw_data_file = os.path.join(cwe_dir, f"cwe_{cwe_id}_raw_results.json")
        processed_data_file = os.path.join(cwe_dir, f"cwe_{cwe_id}_processed_results.json")
        
        for data, filename in [(raw, raw_data_file), (processed, processed_data_file)]:
            output_data = {
                'test_info': {
                    'timestamp': datetime.now().isoformat(),
                    'base_url': self.base_url,
                    'test_cwe_id': cwe_id,
                    'total_endpoints_tested': len(data)
                },
                'results': data
            }

            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                print_success(f"\nResults saved to: {filename}")
                self.logger.info(f"Results saved to: {filename}")
            except Exception as e:
                print_error(f"\nError saving results: {e}")
                self.logger.error(f"Error saving results: {e}")
                

    def run_analysis(self,
                     cwe_id: Union[str, int]) -> None:
        """
        Test all available endpoints and collect results for the given CWE.
        """
        raw_result = {}
        processed_result = {}
        
        print_info(f"Starting data collection for CWE ID: {cwe_id}")
        self.logger.info(f"Starting data collection for CWE ID: {cwe_id}")
        
        # Test each endpoint
        for endpoint, endpoint_func in tqdm(self._get_endpoints(cwe_id)):
            result = self._analyse_endpoint(endpoint)
            raw_result[endpoint] = result

            if result.get('success') and result.get('data'):
                processed_result[endpoint] = endpoint_func(result['data'])
            else:
                processed_result[endpoint] = None
        
        self._save_results(cwe_id, raw_result, processed_result)
        successful = sum(1 \
            for r in raw_result.values() \
                if r and r.get('success', False))
        total = len(raw_result)
        print_info(f"Successful requests for CWE-{cwe_id}: {successful}/{total}")
        

if __name__ == "__main__":
    with open("/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/cwe_analysis/cwe/unique_cwes.txt", 
              "r") as f:
        cwes = f.readlines()
        
    for cwe in tqdm(cwes):
        test_cwe_id = cwe.strip().split("-")[-1]
        analysis = CWEAPIAnalysis()
        analysis.run_analysis(test_cwe_id)