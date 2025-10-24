# =============================================================================================
# Analyse the accuracy of a given tool (LLM or Static) using consolidated results
# Usage:
#   - Evaluate tool accuracy with strict and lenient correctness metrics
#   - Analyse false positive rates and distributions
# =============================================================================================
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import json
import re
from collections import defaultdict
from collections import deque
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from utils.logger.Logger import Logger


class AccuracyAnalysis:
    def __init__(self,
                 tool_type: str,
                 result_path: str,
                 mapping_path: str = ("/home/adnana/workspace/SYNKRASIS/"
                                      "services/CodeSecurity/"
                                      "cwe_analysis/cwe_relationships.json")) -> None:
        """
        Initilise accuracy analysis for either static tools or LLMs.

        Args:
            tool_type (str): Type of tool, either 'static' or 'llm'
            result_path (str): Path to the result file
            mapping_path (str, optional): Path to the mapping file. 
                Defaults to ("/home/s448780/workspace_hcc4/SYNKRASIS/" 
                "services/CodeSecurity/" "cwe_analysis/cwe_relationships.json").
        """
        self.logger = Logger(self.__class__.__name__, "DEBUG")
        self.mapping_path = mapping_path
        self.relationships = self._build_relationships(mapping_path)
        self.tool_type = self._check_tool_type(tool_type)
        self.logger.info(f"Setting up accuracy analysis for '{self.tool_type}' tool")
        self.results = self._load_results(result_path)
        self.output_path = Path(result_path).parent / f"{self.tool_type}_accuracy_analysis.json"
        
        # NOTE: rebase for static check
        analysis_result = self._llm_analysis() \
                          if self.tool_type == 'llm' \
                          else self._static_analysis()
        self.logger.info("Accuracy analysis completed.")
        
        self._save_analysis(analysis_result)
        
    
    def _save_analysis(self,
                       analysis_result: dict) -> None:
        """
        Save the analysis result to the output path.
        
        Args:
            analysis_result (dict): Analysis result to save.
        """
        with open(self.output_path, "w") as f:
            json.dump(analysis_result, f, indent=4)
        self.logger.info("Analysis saved successfully.")
        
        
    def _load_results(self, path: str) -> list:
        """
        Load analysis result with predictions.

        Args:
            path (str): Path to the result file

        Returns:
            list: List of analysis results
        """
        with open(path, "r") as f:
            data = json.load(f)
        self.logger.info(f"Loaded {len(data)} samples from {path}")
        return data
    
    
    def _check_tool_type(self, tool_type: str) -> str:
        """
        Tool type checker, must be 'static' or 'llm'.

        Args:
            tool_type (str): Tool type to check.

        Raises:
            ValueError: If tool type is invalid.

        Returns:
            str: Checked tool type.
        """
        if tool_type not in ['static', 'llm']:
            raise ValueError("'tool_type' must be 'static' or 'llm'")
        return tool_type


    def _build_relationships(self, mapping_path: str) -> dict:
        """
        Build a mapping of CWE relationships from the provided JSON file.
        Relationships are bidirectional but does not include transitive closure.

        Args:
            mapping_path (str): Path to the mapping file.

        Returns:
            dict: Mapping of CWE relationships.
        """
        self.logger.info(f"Loading CWE relationships from {mapping_path}")
        with open(mapping_path, "r") as f:
            cwe_mapping = json.load(f)

        self.logger.info("Relationship mapping loaded.")
        return cwe_mapping


    def are_cwes_directly_related(self, cwe1: str, cwe2: str) -> bool:
        """
        Check if two CWE codes are directly related (with normalisation).
        TRANSITIVE relationships are NOT considered here.
        
        Args:
            cwe1: First CWE code
            cwe2: Second CWE code
            
        Returns:
            bool: True if related, False otherwise
        """
        self.logger.debug(f"Checking direct relationship between {cwe1} and {cwe2}")
        num1 = self.normalise_cwe_number(cwe1)
        num2 = self.normalise_cwe_number(cwe2)
        
        # Direct match
        if num1 == num2:
            self.logger.debug(f"{num1} and {num2} are directly related (exact same code)")
            return True
        
        direct_relationship = num2 in self.relationships.get(num1, set())
        self.logger.debug(f"{num1} and {num2} direct relationship: {direct_relationship}")
        return direct_relationship
    
    
    def are_cwes_transitively_related(self, 
                                      cwe1: str, 
                                      cwe2: str) -> Tuple[bool, Optional[List[str]]]:
        """
        Check if two CWE codes are related either DIRECTLY or TRANSITIVELY.
        
        Args:
            cwe1: First CWE code
            cwe2: Second CWE code
            
        Returns:
            Tuple[bool, list[str] | None]
            - If related, path shows the connection from cwe1 to cwe2
            - If not related, path is None
        """
        self.logger.debug(f"Checking transitive relationship between {cwe1} and {cwe2}")
        num1 = self.normalise_cwe_number(cwe1)
        num2 = self.normalise_cwe_number(cwe2)
                
        # check if they're directly related
        if self.are_cwes_directly_related(num1, num2):
            return True, [num1, num2]
        
        # BFS
        self.logger.debug(f"Performing BFS for transitive relationship between {num1} and {num2}")
        visited: set = {num1}
        queue: deque = deque([(num1, [num1])])
        
        while queue:
            current, path = queue.popleft()
            related_cwes = self.relationships.get(current, set())
            
            for related_cwe in related_cwes:
                if related_cwe == num2:
                    self.logger.debug(f"Found transitive relationship path: {path + [related_cwe]}")
                    return True, path + [related_cwe]
                
                if related_cwe not in visited:
                    visited.add(related_cwe)
                    queue.append((related_cwe, path + [related_cwe]))
        
        self.logger.debug(f"No transitive relationship found between {num1} and {num2}")
        return False, None


    def normalise_cwe_number(self, cwe_code: str) -> str:
        """
        Normalise CWE number by removing leading zeros.
        e.g. CWE-020 and CWE-20 should be treated as the same.
        
        Args:
            cwe_code: CWE code in format "CWE-___" or just number
        
        Returns:
            str: Normalised CWE number as string, e.g "020" -> "20"
        """
        cwe_code = cwe_code.strip()
        
        # Empty input or no CWE e.g. Code has no known vulnerability as true label
        if cwe_code == None or cwe_code == "":
            self.logger.debug("Empty CWE code provided for normalisation")
            return None
        
        if cwe_code.upper().startswith("CWE-"):
            num = cwe_code[4:]
        else:
            num = cwe_code
        
        normalised_num = str(int(num))
        self.logger.debug(f"Normalised '{cwe_code}' to '{normalised_num}'")
        return normalised_num


    def _extract_cwe_number(self, cwe_string: str) -> Optional[str]:
        """
        Extract CWE number from a string using regex.

        Args:
            cwe_string (str): Input string potentially containing a CWE number.

        Returns:
            Optional[str]: Extracted CWE number or None if not found.
        """
        match = re.search(r'CWE[\s]?-[\s]?(\d+)', cwe_string, re.IGNORECASE)
        cwe_number = match.group(1) if match else None
        self.logger.debug(f"Extracted CWE number '{cwe_number}' from string '{cwe_string}'")
        return cwe_number
    
    
    def _get_all_cwes_for_single_static_analysis(self, 
                                                 analysis_results: List[dict]) -> List[str]:
        """
        Extract all CWE numbers from a single static analysis result.
        
        Args:
            analysis_results (List[dict]): List of analysis result dicts from actual result file.
            
        Returns:
            List[str]: List of extracted CWE numbers as strings.
        """
        self.logger.debug("Extracting CWEs from single static analysis results")
        all_cwes = []
        for result in analysis_results:
            cwes_field = result.get('cwes', [])
            if isinstance(cwes_field, list):
                self.logger.debug(f"Found CWEs in list format: {cwes_field}")
                for cwe_string in cwes_field:
                    cwe_num = self._extract_cwe_number(str(cwe_string))
                    if cwe_num:
                        all_cwes.append(cwe_num)
            elif isinstance(cwes_field, str):
                self.logger.debug(f"Found CWEs in string format: {cwes_field}")
                cwe_num = self._extract_cwe_number(cwes_field)
                if cwe_num:
                    all_cwes.append(cwe_num)
        self.logger.debug(f"Extracted CWEs: {all_cwes}")
        return all_cwes
    
    
    def _get_all_cwes_for_single_llm_analysis(self, 
                                              parsed_response: dict) -> List[str]:
        """
        Extract all CWE numbers from a single LLM analysis result.
        
        Args:
            parsed_response (dict): Parsed response dict from actual result file.
        
        Returns:
            List[str]: List of extracted CWE numbers as strings.
        """
        self.logger.debug("Extracting CWEs from single LLM analysis parsed response")
        cwe_list = parsed_response.get('cwe', [])
        all_cwes = []
        for cwe in cwe_list:
            cwe_num = self._extract_cwe_number(str(cwe))
            if cwe_num:
                all_cwes.append(cwe_num)
        self.logger.debug(f"Extracted CWEs: {all_cwes}")
        return all_cwes
    
    
    def _evaluate_single_sample(self, 
                                true_label: str, 
                                tool_cwes: List[str]) -> Dict:
        """
        Evaluate a single sample's predictions.
        Args:
            true_label (str): The true CWE label for the sample.
            tool_cwes (List[str]): List of CWE codes predicted by the tool.
        
        
        
        Returns: 
            dict: {strict_correct: bool, 
                   lenient_correct: bool, 
                   true_positives: list of CWEs, 
                   false_positives: list of CWEs, 
                   fp_count: int, 
                   noise_ratio: float (FPs / total reported),
                   complete_miss: bool}
        """
        self.logger.debug(f"Evaluating sample with true label '{true_label}' and predicted CWEs: {tool_cwes}")
        true_label_norm = self.normalise_cwe_number(true_label)
        
        if not tool_cwes:
            return self._handle_no_reported_cwe(true_label_norm)
        
        true_positives = []
        false_positives = []
        
        for cwe in tool_cwes:
            cwe_norm = self.normalise_cwe_number(cwe)
            # NOTE: Cluster beforehand to make this faster
            is_related, _ = self.are_cwes_transitively_related(true_label_norm, cwe_norm)
            
            if is_related:
                true_positives.append(cwe_norm)
            else:
                false_positives.append(cwe_norm)
        
        fp_count = len(false_positives)
        noise_ratio = fp_count / len(tool_cwes) if tool_cwes else 0.0
        
        # Strict: found true label AND no false positives
        strict_correct = len(true_positives) > 0 and fp_count == 0
        
        # Lenient: found true label (ignoring false positives)
        lenient_correct = len(true_positives) > 0
        
        # Complete miss: didn't find true label
        complete_miss = len(true_positives) == 0
        
        return {
            'strict_correct': strict_correct,
            'lenient_correct': lenient_correct,
            'true_positives': true_positives,
            'false_positives': false_positives,
            'fp_count': fp_count,
            'noise_ratio': noise_ratio,
            'complete_miss': complete_miss
        }
        
    
    def _handle_no_reported_cwe(self, true_label_norm: str) -> Dict:
        """
        Handle case where tool reported no CWEs.
        
        Args:
            true_label_norm (str): Normalised true CWE label.
        
        Returns:
            dict: Evaluation result indicating complete miss if true label exists.
        """
        self.logger.debug("Tool reported no CWEs")
        evaluation = {
            'strict_correct': True if true_label_norm == None else False,
            'lenient_correct': True if true_label_norm == None else False,
            'true_positives': [None] if true_label_norm == None else [],
            'false_positives': [],
            'fp_count': 0,
            'noise_ratio': 0.0,
            'complete_miss': False if true_label_norm == None else True
        }
        self.logger.debug(f"Evaluation result: {evaluation}")
        return evaluation
    
    
    def _llm_analysis(self) -> List[dict]:
        """
        Analyse LLM results
        """
        # Get all unique LLM models
        llm_models = set()
        for sample in self.results:
            for analysis in sample.get('analysis', []):
                if 'llm_model' in analysis:
                    llm_models.add(analysis['llm_model'])
        
        llm_models = sorted(list(llm_models))
        
        # Initialise metrics for each model
        model_metrics = {}
        for model in llm_models:
            model_metrics[model] = {
                'total_samples': 0,
                'strict_correct': 0,
                'lenient_correct': 0,
                'complete_miss': 0,
                'fp_counts': [],
                'noise_ratios': [],
                'fp_distribution': defaultdict(int),
                'samples_with_detections': 0,
                'complete_miss_wo_fp': 0
            }
        
        # Process each sample
        for sample in self.results:
            true_label = sample.get('true_label')
            analysis_list = sample.get('analysis', []) # predictions
            
            for analysis in analysis_list:  
                model = analysis['llm_model']
                model_metrics[model]['total_samples'] += 1
                
                parsed_response = analysis.get('parsed_response', {})
                tool_cwes = self._get_all_cwes_for_single_llm_analysis(parsed_response)
                
                evaluation = self._evaluate_single_sample(true_label, tool_cwes)
                
                # No CWE incorrectly reported
                if evaluation['complete_miss'] == True and evaluation['false_positives'] == []:
                    model_metrics[model]['complete_miss_wo_fp'] += 1
                
                if evaluation['strict_correct']:
                    model_metrics[model]['strict_correct'] += 1
                
                if evaluation['lenient_correct']:
                    model_metrics[model]['lenient_correct'] += 1
                
                if evaluation['complete_miss']:
                    model_metrics[model]['complete_miss'] += 1
                
                if tool_cwes:  # If tool detected something
                    model_metrics[model]['samples_with_detections'] += 1
                    model_metrics[model]['fp_counts'].append(evaluation['fp_count'])
                    model_metrics[model]['noise_ratios'].append(evaluation['noise_ratio'])
                    model_metrics[model]['fp_distribution'][evaluation['fp_count']] += 1
        
        # Print reports for each model
        results = []
        for model in llm_models:
            result = self._print_tool_report(model, model_metrics[model])
            results.append(result)

        return results

    def _static_analysis(self) -> List[dict]:
        """
        Analyse static tool results
        """
        # Get all unique static tools
        static_tools = set()
        for sample in self.results:
            for analysis in sample.get('analysis', []):
                if 'tool' in analysis:
                    static_tools.add(analysis['tool'])
        
        static_tools = sorted(list(static_tools))
        
        # Initialize metrics for each tool
        tool_metrics = {}
        for tool in static_tools:
            tool_metrics[tool] = {
                'total_samples': 0,
                'strict_correct': 0,
                'lenient_correct': 0,
                'complete_miss': 0,
                'fp_counts': [],
                'noise_ratios': [],
                'fp_distribution': defaultdict(int),
                'samples_with_detections': 0,
                'complete_miss_wo_fp': 0
            }
        
        # Process each sample
        for sample in self.results:
            true_label = sample.get('true_label')
            analysis_list = sample.get('analysis', [])
            
            for analysis in analysis_list:
                if 'tool' not in analysis:
                    continue
                    
                tool = analysis['tool']
                tool_metrics[tool]['total_samples'] += 1
                
                analysis_results = analysis.get('analysis_results', [])
                tool_cwes = self._get_all_cwes_for_single_static_analysis(analysis_results)
                
                evaluation = self._evaluate_single_sample(true_label, tool_cwes)
                
                # No CWE incorrectly reported
                if evaluation['complete_miss'] == True and evaluation['false_positives'] == []:
                    tool_metrics[tool]['complete_miss_wo_fp'] += 1
                
                if evaluation['strict_correct']:
                    tool_metrics[tool]['strict_correct'] += 1
                
                if evaluation['lenient_correct']:
                    tool_metrics[tool]['lenient_correct'] += 1
                
                if evaluation['complete_miss']:
                    tool_metrics[tool]['complete_miss'] += 1
                
                if tool_cwes:  # If tool detected something
                    tool_metrics[tool]['samples_with_detections'] += 1
                    tool_metrics[tool]['fp_counts'].append(evaluation['fp_count'])
                    tool_metrics[tool]['noise_ratios'].append(evaluation['noise_ratio'])
                    tool_metrics[tool]['fp_distribution'][evaluation['fp_count']] += 1
        
        # Print reports for each tool
        results = []
        for tool in static_tools:
            result = self._print_tool_report(tool, tool_metrics[tool])
            results.append(result)
        
        return results
        
    
    
    def _print_tool_report(self, 
                           tool_name: str, 
                           metrics: Dict) -> dict:
        """
        Print formatted report for a single tool
        
        Args:
            tool_name (str): Name of the tool
            metrics (Dict): Metrics dictionary for the tool
        
        Returns:
            dict: Summary of the tool's metrics
        """
        total = metrics['total_samples']
        strict = metrics['strict_correct']
        lenient = metrics['lenient_correct']
        miss = metrics['complete_miss']
        detections = metrics['samples_with_detections']
        complete_miss_wo_fp = metrics['complete_miss_wo_fp'] # secure prediction
        with_noise = lenient - strict + miss - complete_miss_wo_fp
        fp_dist = metrics['fp_distribution'] # will report strict and noise
        max_fp = max(fp_dist.keys()) if fp_dist else 0
        avg_fp_for_noisy_preds = self._get_avg_fp_count_from_noisy_predictions(fp_dist, with_noise)
        avg_fp_for_all_preds = self._get_avg_fp_count_from_noisy_predictions(fp_dist, detections)
        
        print(f"\nTool: {tool_name} ({total} samples)")
        print("━" * 80)
        print("CORRECTNESS")
        print("━" * 80)
        print(f"Total detections made: {detections}/{total} ({detections/total*100:.1f}%)")
        print(f"Strict Correct:    {strict}/{total} ({strict/total*100:.1f}%) | Perfect detection, no noise")
        print(f"Lenient Correct:   {lenient}/{total} ({lenient/total*100:.1f}%) | Found vulnerability, ignoring extras")
        print(f"Predictions with Noise: {with_noise}/{total} ({with_noise/total*100:.1f}%) | Detected vulnerability but with FPs")
        print(f"Predicted secure: {complete_miss_wo_fp}/{total} ({complete_miss_wo_fp/total*100:.1f}%) | No vulnerabilities detected")
        print("\n" + "━" * 80)
        print("FALSE POSITIVE ANALYSIS")
        print("━" * 80)
        print(f"False positive distribution: {fp_dist}")
        print(f"Average FP count for noisy predictions: {avg_fp_for_noisy_preds:.2f}")
        print(f"Average FP count for all predictions with detections: {avg_fp_for_all_preds:.2f}")
        print(f"Maximum FP count observed: {max_fp}")
        print("━" * 80)
        print("\n")
        
        return {
            'tool_name': tool_name,
            'total_samples': total,
            'detections_made': detections,
            'strict_correct': strict,
            'lenient_correct': lenient,
            'total_miss': miss,
            'predictions_with_noise': with_noise,
            'predicted_secure': complete_miss_wo_fp,
            'fp_distribution': fp_dist,
            'avg_fp_noisy': avg_fp_for_noisy_preds,
            'avg_fp_all': avg_fp_for_all_preds,
            'max_fp': max_fp
        }
        
    
    def _get_avg_fp_count_from_noisy_predictions(self,
                                                 fp_distribution: Dict[int, int],
                                                 noisy_prediction_count: int) -> float:
        """
        Calculate average FP count from noisy predictions.

        Args:
            fp_distribution (Dict[int, int]): Distribution of FP counts.
            noisy_prediction_count (int): Number of noisy predictions.

        Returns:
            float: Average FP count for noisy predictions.
        """
        if noisy_prediction_count == 0:
            return 0.0

        total_fp = sum(fp * count for fp, count in fp_distribution.items() if fp > 0)
        self.logger.debug(f"Total FPs from noisy predictions: {total_fp}")
        self.logger.debug(f"On Average FP count for noisy predictions: {total_fp / noisy_prediction_count}")
        
        return total_fp / noisy_prediction_count


if __name__ == "__main__":
    # LLMs
    llm_path = ("services/CodeSecurity/exp_dir_SVEN_python/"
                "SVEN_qwen2_5_coder_32b_mistral_latest_qwen2_5_coder_latest_"
                "llama3_1_latest_phi4_latest_deepseek_coder_6_7b_devstral_24b.json")
    
    print("=" * 80)
    print("LLM ANALYSIS")
    print("=" * 80)
    llm_analyser = AccuracyAnalysis(tool_type='llm', result_path=llm_path)
    
    # Static tools
    # static_path = ("services/CodeSecurity/"
    #                "exp_dir_SecurityEval/"
    #                "SecurityEval_consolidated_evaluation_results.json")
    
    # print("=" * 80)
    # print("STATIC TOOLS ANALYSIS")
    # print("=" * 80)
    # static_analyser = AccuracyAnalysis(tool_type='static', result_path=static_path)