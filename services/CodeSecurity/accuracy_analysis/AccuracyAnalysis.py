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

from utils.logger.Logger import Logger


class AccuracyAnalysis:
    def __init__(self,
                 tool_type: str,
                 result_path: str,
                 mapping_path: str = ("/home/s448780/workspace_hcc4/SYNKRASIS/"
                                      "services/CodeSecurity/"
                                      "cwe_analysis/cwe_relationships.json")) -> None:
        self.logger = Logger(self.__class__.__name__, "DEBUG")
        self.mapping_path = mapping_path
        self.relationships = self._build_relationships(mapping_path)
        self.tool_type = self._check_tool_type(tool_type)
        self.results = self._load_results(result_path)
        
        if self.tool_type == 'llm':
            self._llm_analysis()
        else:
            self._static_analysis()
            
        
    def _load_results(self, path: str) -> list:
        with open(path, "r") as f:
            data = json.load(f)
        return data
    
    
    def _check_tool_type(self, tool_type: str) -> str:
        if tool_type not in ['static', 'llm']:
            raise ValueError("'tool_type' must be 'static' or 'llm'")
        return tool_type


    def _build_relationships(self, mapping_path: str) -> dict:
        with open(mapping_path, "r") as f:
            cwe_mapping = json.load(f)
        return cwe_mapping


    def are_cwes_directly_related(self, cwe1: str, cwe2: str) -> bool:
        """
        Check if two CWE codes are directly related (with normalisation)
        
        Args:
            cwe1: First CWE code
            cwe2: Second CWE code
            
        Returns:
            bool: True if related, False otherwise
        """
        num1 = self.normalise_cwe_number(cwe1)
        num2 = self.normalise_cwe_number(cwe2)
        
        # Direct match
        if num1 == num2:
            return True
        
        # Check via relationships
        return num2 in self.relationships.get(num1, set())
    
    
    def are_cwes_transitively_related(self, 
                                      cwe1: str, 
                                      cwe2: str) -> Tuple[bool, Optional[List[str]]]:
        """
        Check if two CWE codes are related either directly or transitively.
        
        Args:
            cwe1: First CWE code
            cwe2: Second CWE code
            
        Returns:
            Tuple of (is_related: bool, path: list[str] | None)
            - If related, path shows the connection from cwe1 to cwe2
            - If not related, path is None
        """
        num1 = self.normalise_cwe_number(cwe1)
        num2 = self.normalise_cwe_number(cwe2)
        
        if num1 == num2:
            return True, [num1]
        
        # check if they're directly related
        if self.are_cwes_directly_related(num1, num2):
            return True, [num1, num2]
        
        # BFS
        visited = {num1}
        queue = deque([(num1, [num1])])
        
        while queue:
            current, path = queue.popleft()
            related_cwes = self.relationships.get(current, set())
            
            for related_cwe in related_cwes:
                if related_cwe == num2:
                    return True, path + [related_cwe]
                
                if related_cwe not in visited:
                    visited.add(related_cwe)
                    queue.append((related_cwe, path + [related_cwe]))
        
        return False, None


    def normalise_cwe_number(self, cwe_code: str) -> str:
        """
        Normalise CWE number by removing leading zeros.
        CWE-020 and CWE-20 should be treated as the same.
        
        Args:
            cwe_code: CWE code in format "CWE-___" or just number
        
        Returns:
            str: Normalised CWE number as string, e.g "020" -> "20"
        """
        cwe_code = cwe_code.strip()
        if cwe_code.startswith("CWE-"):
            num = cwe_code[4:]
        else:
            num = cwe_code
        
        # Convert to int and back to remove leading zeros
        return str(int(num))
    
    
    def _extract_cwe_number(self, cwe_string: str) -> Optional[str]:
        match = re.search(r'CWE[\s]?-[\s]?(\d+)', cwe_string, re.IGNORECASE)
        return match.group(1) if match else None
    
    
    def _get_all_cwes_for_single_static_analysis(self, analysis_results: List[dict]) -> List[str]:
        all_cwes = []
        for result in analysis_results:
            cwes_field = result.get('cwes', [])
            if isinstance(cwes_field, list):
                for cwe_string in cwes_field:
                    cwe_num = self._extract_cwe_number(str(cwe_string))
                    if cwe_num:
                        all_cwes.append(cwe_num)
            elif isinstance(cwes_field, str):
                cwe_num = self._extract_cwe_number(cwes_field)
                if cwe_num:
                    all_cwes.append(cwe_num)
        return all_cwes
    
    
    def _get_all_cwes_for_single_llm_analysis(self, parsed_response: dict) -> List[str]:
        cwe_list = parsed_response.get('cwe', [])
        all_cwes = []
        for cwe in cwe_list:
            cwe_num = self._extract_cwe_number(str(cwe))
            if cwe_num:
                all_cwes.append(cwe_num)
        return all_cwes
    
    
    def _evaluate_single_sample(self, true_label: str, tool_cwes: List[str]) -> Dict:
        """
        Evaluate a single sample's predictions
        
        Returns dict with:
        - strict_correct: bool
        - lenient_correct: bool
        - true_positives: list of CWEs
        - false_positives: list of CWEs
        - fp_count: int
        - noise_ratio: float (FPs / total reported)
        """
        true_label_norm = self.normalise_cwe_number(true_label)
        
        if not tool_cwes:
            # Tool reported nothing
            return {
                'strict_correct': False,
                'lenient_correct': False,
                'true_positives': [],
                'false_positives': [],
                'fp_count': 0,
                'noise_ratio': 0.0,
                'complete_miss': True
            }
        
        true_positives = []
        false_positives = []
        
        for cwe in tool_cwes:
            cwe_norm = self.normalise_cwe_number(cwe)
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
    
    
    def _llm_analysis(self):
        """Analyse LLM results"""
        # Get all unique LLM models
        llm_models = set()
        for sample in self.results:
            for analysis in sample.get('analysis', []):
                if 'llm_model' in analysis:
                    llm_models.add(analysis['llm_model'])
        
        llm_models = sorted(list(llm_models))
        
        # Initialize metrics for each model
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
                'samples_with_detections': 0
            }
        
        # Process each sample
        for sample in self.results:
            true_label = sample.get('true_label')
            analysis_list = sample.get('analysis', [])
            
            for analysis in analysis_list:
                if 'llm_model' not in analysis:
                    continue
                    
                model = analysis['llm_model']
                model_metrics[model]['total_samples'] += 1
                
                parsed_response = analysis.get('parsed_response', {})
                tool_cwes = self._get_all_cwes_for_single_llm_analysis(parsed_response)
                
                evaluation = self._evaluate_single_sample(true_label, tool_cwes)
                
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
        for model in llm_models:
            self._print_tool_report(model, model_metrics[model])
    
    
    def _static_analysis(self):
        """Analyse static tool results"""
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
                'samples_with_detections': 0
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
        for tool in static_tools:
            self._print_tool_report(tool, tool_metrics[tool])
    
    
    def _print_tool_report(self, tool_name: str, metrics: Dict):
        """Print formatted report for a single tool"""
        total = metrics['total_samples']
        strict = metrics['strict_correct']
        lenient = metrics['lenient_correct']
        miss = metrics['complete_miss']
        detections = metrics['samples_with_detections']
        
        print(f"\nTool: {tool_name} ({total} samples)")
        print("━" * 80)
        print("CORRECTNESS")
        print("━" * 80)
        print(f"Strict Correct:    {strict}/{total} ({strict/total*100:.1f}%)  ← Perfect detection, no noise")
        print(f"Lenient Correct:   {lenient}/{total} ({lenient/total*100:.1f}%)  ← Found vulnerability, ignoring extras")
        print(f"Complete Miss:     {miss}/{total} ({miss/total*100:.1f}%)  ← Failed to detect")
        
        print("\n" + "━" * 80)
        print("FALSE POSITIVE ANALYSIS")
        print("━" * 80)
        
        if detections > 0:
            samples_with_fps = sum(1 for fp in metrics['fp_counts'] if fp > 0)
            print((f"Samples with FPs:  {samples_with_fps}/{detections} "
                   f"({samples_with_fps/detections*100:.1f}% of detections had noise)"))
            
            print("\nFP Count Distribution:")
            fp_dist = metrics['fp_distribution']
            max_fp = max(fp_dist.keys()) if fp_dist else 0
            
            # Group 3+ FPs together
            for i in range(max_fp + 1):
                if i <= 2:
                    count = fp_dist.get(i, 0)
                    pct = count / detections * 100 if detections > 0 else 0
                    print(f"  {i} FPs:  {count} samples ({pct:.1f}%)")
                elif i == 3:
                    count_3plus = sum(fp_dist.get(j, 0) for j in range(3, max_fp + 1))
                    pct = count_3plus / detections * 100 if detections > 0 else 0
                    print(f"  3+ FPs: {count_3plus} samples ({pct:.1f}%)")
                    break
            
            # Calculate averages
            avg_fp_all = sum(metrics['fp_counts']) / len(metrics['fp_counts']) if metrics['fp_counts'] else 0
            fp_counts_nonzero = [fp for fp in metrics['fp_counts'] if fp > 0]
            avg_fp_when_fp = sum(fp_counts_nonzero) / len(fp_counts_nonzero) if fp_counts_nonzero else 0
            median_fp = sorted(metrics['fp_counts'])[len(metrics['fp_counts'])//2] if metrics['fp_counts'] else 0
            avg_noise = sum(metrics['noise_ratios']) / len(metrics['noise_ratios']) if metrics['noise_ratios'] else 0
            
            print(f"\nAverage FPs per sample (all):        {avg_fp_all:.1f}")
            print(f"Average FPs per sample (when FP>0):  {avg_fp_when_fp:.1f}")
            print(f"Median FPs:                          {median_fp}")
            print(f"Average Noise Ratio:                 {avg_noise*100:.1f}%")
        else:
            print("No detections to analyse")
        
        print("\n")


if __name__ == "__main__":
    # Example usage for LLM
    llm_path = ("/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/"
                "exp_dir_SecurityEval/"
                "SecurityEval_qwen2_5_coder_32b_mistral_latest_qwen2_5_coder_latest_llama3_1_latest.json")
    
    print("=" * 80)
    print("LLM ANALYSIS")
    print("=" * 80)
    llm_analyser = AccuracyAnalysis(tool_type='llm', result_path=llm_path)
    
    # Example usage for static tools
    static_path = ("/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/"
                   "exp_dir_SecurityEval/"
                   "SecurityEval_consolidated_evaluation_results.json")
    
    print("\n" + "=" * 80)
    print("STATIC TOOLS ANALYSIS")
    print("=" * 80)
    static_analyser = AccuracyAnalysis(tool_type='static', result_path=static_path)