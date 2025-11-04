# =============================================================================================
# Analyse the accuracy of a given tool (LLM or Static) using consolidated results
# Uses hop-based distance metrics with tunable tolerance
# =============================================================================================
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import json
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from utils.logger.Logger import Logger


class AccuracyAnalysis:
    def __init__(self,
                 tool_type: str,
                 result_path: str,
                 tolerance: int = 1,
                 immediate_rel_path: str = "services/CodeSecurity/cwe_analysis/cwe_immediate_relationships.json",
                 distance_map_path: str = "services/CodeSecurity/cwe_analysis/cwe_distance_map.json",
                 root_categories_path: str = "services/CodeSecurity/cwe_analysis/cwe_root_categories.json") -> None:
        """
        Initialise accuracy analysis for either static tools or LLMs.

        Args:
            tool_type (str): Type of tool, either 'static' or 'llm'
            result_path (str): Path to the result file
            tolerance (int): Tolerance for hop-based accuracy (default=1)
            immediate_rel_path (str): Path to immediate relationships file
            distance_map_path (str): Path to distance map file
            root_categories_path (str): Path to root categories file
        """
        self.logger = Logger(self.__class__.__name__, "DEBUG")
        self.tolerance = tolerance
        
        # Load relationship data
        self.immediate_relationships = self._load_json(immediate_rel_path)
        self.distance_map = self._load_json(distance_map_path)
        self.root_categories = self._load_json(root_categories_path)
        
        self.tool_type = self._check_tool_type(tool_type)
        self.logger.info(f"Setting up accuracy analysis for '{self.tool_type}' tool with tolerance={tolerance}")
        
        self.results = self._load_results(result_path)
        self.output_path = Path(result_path).parent / f"{self.tool_type}_accuracy_analysis.json"
        
        # Run analysis
        analysis_result = self._llm_analysis() if self.tool_type == 'llm' else self._static_analysis()
        self.logger.info("Accuracy analysis completed.")
        
        self._save_analysis(analysis_result)
    
    def _load_json(self, path: str) -> dict:
        """Load JSON file"""
        self.logger.info(f"Loading {path}")
        with open(path, 'r') as f:
            return json.load(f)
    
    def _save_analysis(self, analysis_result: dict) -> None:
        """Save the analysis result to the output path."""
        with open(self.output_path, "w") as f:
            json.dump(analysis_result, f, indent=4)
        self.logger.info(f"Analysis saved to {self.output_path}")
        
    def _load_results(self, path: str) -> list:
        """Load analysis result with predictions."""
        with open(path, "r") as f:
            data = json.load(f)
        self.logger.info(f"Loaded {len(data)} samples from {path}")
        return data
    
    def _check_tool_type(self, tool_type: str) -> str:
        """Tool type checker, must be 'static' or 'llm'."""
        if tool_type not in ['static', 'llm']:
            raise ValueError("'tool_type' must be 'static' or 'llm'")
        return tool_type

    def normalise_cwe_number(self, cwe_code: str) -> str:
        """
        Normalise CWE number by removing leading zeros.
        e.g. CWE-020 and CWE-20 should be treated as the same.
        """
        if cwe_code is None or cwe_code == "":
            return None
        
        cwe_code = cwe_code.strip()
        
        if cwe_code.upper().startswith("CWE-"):
            num = cwe_code[4:]
        else:
            num = cwe_code
        
        normalised_num = str(int(num))
        return normalised_num

    def _extract_cwe_number(self, cwe_string: str) -> Optional[str]:
        """Extract CWE number from a string using regex."""
        match = re.search(r'CWE[\s]?-[\s]?(\d+)', cwe_string, re.IGNORECASE)
        return match.group(1) if match else None
    
    def _get_all_cwes_for_single_static_analysis(self, analysis_results: List[dict]) -> List[str]:
        """Extract all CWE numbers from a single static analysis result."""
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
        """Extract all CWE numbers from a single LLM analysis result."""
        cwe_list = parsed_response.get('cwe', [])
        all_cwes = []
        for cwe in cwe_list:
            cwe_num = self._extract_cwe_number(str(cwe))
            if cwe_num:
                all_cwes.append(cwe_num)
        return all_cwes
    
    def _enrich_prediction(self, true_label: str, predicted_cwe: str) -> Dict:
        """
        Enrich a single prediction with relationship metadata.
        
        Returns:
            dict: {
                "hop_distance": int,
                "is_immediate_family": bool,
                "same_root_category": bool,
                "true_root": str,
                "pred_root": str or list
            }
        """
        true_norm = self.normalise_cwe_number(true_label)
        pred_norm = self.normalise_cwe_number(predicted_cwe)
        
        # Get hop distance
        if true_norm == pred_norm:
            hop_distance = 0
        else:
            hop_distance = self.distance_map.get(true_norm, {}).get(pred_norm, float('inf'))
        
        # Check immediate family
        is_immediate_family = False
        if true_norm in self.immediate_relationships:
            immediate = self.immediate_relationships[true_norm]
            is_immediate_family = (
                pred_norm in immediate.get('immediate_parents', []) or
                pred_norm in immediate.get('immediate_children', []) or
                pred_norm == true_norm
            )
        
        # Check same root category
        true_root = self.root_categories.get(true_norm)
        pred_root = self.root_categories.get(pred_norm)
        
        # Handle cases where roots might be lists
        if isinstance(true_root, list) and isinstance(pred_root, list):
            same_root = bool(set(true_root) & set(pred_root))
        elif isinstance(true_root, list):
            same_root = pred_root in true_root
        elif isinstance(pred_root, list):
            same_root = true_root in pred_root
        else:
            same_root = true_root == pred_root
        
        return {
            "hop_distance": hop_distance,
            "is_immediate_family": is_immediate_family,
            "same_root_category": same_root,
            "true_root": true_root,
            "pred_root": pred_root
        }
    
    def _enrich_all_predictions(self, true_label: str, predicted_cwes: List[str]) -> Dict:
        """
        Enrich all predictions for a single sample.
        
        Returns:
            dict: {
                "predicted_cwe": {
                    "hop_distance": int,
                    "is_immediate_family": bool,
                    "same_root_category": bool,
                    ...
                }
            }
        """
        enriched = {}
        for pred_cwe in predicted_cwes:
            pred_norm = self.normalise_cwe_number(pred_cwe)
            enriched[pred_norm] = self._enrich_prediction(true_label, pred_cwe)
        
        return enriched
    
    def _evaluate_at_hop_level(self, enriched_predictions: Dict, hop_level: int) -> Dict:
        """
        Evaluate predictions at a specific hop level with tolerance.
        
        Args:
            enriched_predictions: Dict of predictions with metadata
            hop_level: The hop level to evaluate at
        
        Returns:
            dict: {
                "perfect": list of CWEs with hop <= hop_level,
                "acceptable": list of CWEs with hop_level < hop <= hop_level + tolerance,
                "false_positive": list of CWEs with hop > hop_level + tolerance,
                "perfect_count": int,
                "acceptable_count": int,
                "fp_count": int,
                "has_perfect": bool,
                "has_acceptable": bool,
                "best_hop": int (minimum hop distance in predictions)
            }
        """
        perfect = []
        acceptable = []
        false_positive = []
        
        # Track best (minimum) hop distance
        best_hop = float('inf')
        
        for cwe, metadata in enriched_predictions.items():
            hop = metadata['hop_distance']
            
            # Update best hop
            if hop < best_hop:
                best_hop = hop
            
            # Classify prediction
            if hop <= hop_level:
                perfect.append(cwe)
            elif hop <= hop_level + self.tolerance:
                acceptable.append(cwe)
            else:
                false_positive.append(cwe)
        
        return {
            "perfect": perfect,
            "acceptable": acceptable,
            "false_positive": false_positive,
            "perfect_count": len(perfect),
            "acceptable_count": len(acceptable),
            "fp_count": len(false_positive),
            "has_perfect": len(perfect) > 0,
            "has_acceptable": len(acceptable) > 0,
            "best_hop": best_hop if best_hop != float('inf') else None
        }
    
    def _llm_analysis(self) -> Dict:
        """Analyse LLM results with hop-based metrics"""
        # Get all unique LLM models
        llm_models = set()
        for sample in self.results:
            for analysis in sample.get('analysis', []):
                if 'llm_model' in analysis:
                    llm_models.add(analysis['llm_model'])
        
        llm_models = sorted(list(llm_models))
        
        # Store enriched data and metrics
        model_results = {}
        
        for model in llm_models:
            model_results[model] = {
                'enriched_samples': [],
                'total_samples': 0,
                'samples_with_predictions': 0
            }
        
        # Process each sample
        for sample in self.results:
            true_label = sample.get('true_label')
            true_norm = self.normalise_cwe_number(true_label)
            
            if not true_norm:
                continue
            
            analysis_list = sample.get('analysis', [])
            
            for analysis in analysis_list:
                model = analysis['llm_model']
                model_results[model]['total_samples'] += 1
                
                parsed_response = analysis.get('parsed_response', {})
                tool_cwes = self._get_all_cwes_for_single_llm_analysis(parsed_response)
                
                if not tool_cwes:
                    # No predictions made
                    enriched_sample = {
                        'true_label': true_norm,
                        'predictions': {},
                        'has_predictions': False
                    }
                else:
                    model_results[model]['samples_with_predictions'] += 1
                    enriched_predictions = self._enrich_all_predictions(true_label, tool_cwes)
                    
                    enriched_sample = {
                        'true_label': true_norm,
                        'predictions': enriched_predictions,
                        'has_predictions': True
                    }
                
                model_results[model]['enriched_samples'].append(enriched_sample)
        
        # Calculate metrics at different hop levels
        final_results = []
        for model in llm_models:
            model_data = model_results[model]
            result = self._calculate_hop_metrics(model, model_data)
            final_results.append(result)
            self._print_model_report(model, result)
        
        return {
            'tolerance': self.tolerance,
            'models': final_results
        }
    
    def _static_analysis(self) -> Dict:
        """Analyse static tool results with hop-based metrics"""
        # Get all unique static tools
        static_tools = set()
        for sample in self.results:
            for analysis in sample.get('analysis', []):
                if 'tool' in analysis:
                    static_tools.add(analysis['tool'])
        
        static_tools = sorted(list(static_tools))
        
        # Store enriched data and metrics
        tool_results = {}
        
        for tool in static_tools:
            tool_results[tool] = {
                'enriched_samples': [],
                'total_samples': 0,
                'samples_with_predictions': 0
            }
        
        # Process each sample
        for sample in self.results:
            true_label = sample.get('true_label')
            true_norm = self.normalise_cwe_number(true_label)
            
            if not true_norm:
                continue
            
            analysis_list = sample.get('analysis', [])
            
            for analysis in analysis_list:
                if 'tool' not in analysis:
                    continue
                
                tool = analysis['tool']
                tool_results[tool]['total_samples'] += 1
                
                analysis_results = analysis.get('analysis_results', [])
                tool_cwes = self._get_all_cwes_for_single_static_analysis(analysis_results)
                
                if not tool_cwes:
                    enriched_sample = {
                        'true_label': true_norm,
                        'predictions': {},
                        'has_predictions': False
                    }
                else:
                    tool_results[tool]['samples_with_predictions'] += 1
                    enriched_predictions = self._enrich_all_predictions(true_label, tool_cwes)
                    
                    enriched_sample = {
                        'true_label': true_norm,
                        'predictions': enriched_predictions,
                        'has_predictions': True
                    }
                
                tool_results[tool]['enriched_samples'].append(enriched_sample)
        
        # Calculate metrics at different hop levels
        final_results = []
        for tool in static_tools:
            tool_data = tool_results[tool]
            result = self._calculate_hop_metrics(tool, tool_data)
            final_results.append(result)
            self._print_model_report(tool, result)
        
        return {
            'tolerance': self.tolerance,
            'tools': final_results
        }
    
    def _calculate_hop_metrics(self, tool_name: str, tool_data: Dict) -> Dict:
        """
        Calculate metrics at different hop levels (0 to 13).
        
        Returns comprehensive metrics for each hop level.
        """
        total_samples = tool_data['total_samples']
        samples_with_predictions = tool_data['samples_with_predictions']
        enriched_samples = tool_data['enriched_samples']
        
        # Calculate average predictions per sample
        total_predictions = sum(len(s['predictions']) for s in enriched_samples if s['has_predictions'])
        avg_predictions_per_sample = total_predictions / samples_with_predictions if samples_with_predictions > 0 else 0
        
        # Find max hop distance to determine range
        max_hop = 0
        for sample in enriched_samples:
            if sample['has_predictions']:
                for metadata in sample['predictions'].values():
                    if metadata['hop_distance'] != float('inf'):
                        max_hop = max(max_hop, metadata['hop_distance'])
        
        # Calculate metrics for each hop level
        hop_metrics = {}
        samples_correct_cumulative = 0  # At start of loop
        
        for hop_level in range(max_hop + 1):
            perfect_count = 0
            acceptable_count = 0
            fp_count = 0
            samples_with_perfect = 0
            samples_with_acceptable = 0
            samples_with_fp = 0
            samples_with_zero_fp = 0
            best_hop_distribution = defaultdict(int)
            fp_distribution = defaultdict(int)
            
            for sample in enriched_samples:
                if not sample['has_predictions']:
                    continue
                
                evaluation = self._evaluate_at_hop_level(sample['predictions'], hop_level)
                
                perfect_count += evaluation['perfect_count']
                acceptable_count += evaluation['acceptable_count']
                fp_count += evaluation['fp_count']
                
                # Track samples with at least one perfect/acceptable
                if evaluation['has_perfect']:
                    samples_with_perfect += 1
                if evaluation['has_acceptable']:
                    samples_with_acceptable += 1
                
                # Track FP distribution
                if evaluation['fp_count'] > 0:
                    samples_with_fp += 1
                    fp_distribution[evaluation['fp_count']] += 1
                else:
                    samples_with_zero_fp += 1
                
                # Track best hop per sample
                if evaluation['best_hop'] is not None:
                    best_hop_distribution[evaluation['best_hop']] += 1
            
            # Calculate average FPs per sample (for samples with predictions)
            avg_fp_per_sample = fp_count / samples_with_predictions if samples_with_predictions > 0 else 0
            
            # Calculate average FPs per sample with FPs
            avg_fp_per_sample_with_fp = fp_count / samples_with_fp if samples_with_fp > 0 else 0
            
            hop_metrics[f"hop_{hop_level}"] = {
                "perfect_predictions": perfect_count,
                "acceptable_predictions": acceptable_count,
                "false_positives": fp_count,
                "samples_with_perfect": samples_with_perfect,
                "samples_with_acceptable": samples_with_acceptable,
                "samples_with_fp": samples_with_fp,
                "samples_with_zero_fp": samples_with_zero_fp,
                "perfect_accuracy": samples_with_perfect / total_samples if total_samples > 0 else 0,
                "acceptable_accuracy": samples_with_acceptable / total_samples if total_samples > 0 else 0,
                "avg_fp_per_sample": avg_fp_per_sample,
                "avg_fp_per_sample_with_fp": avg_fp_per_sample_with_fp,
                "fp_distribution": dict(fp_distribution),
                "best_hop_distribution": dict(best_hop_distribution)
            }
        
        return {
            'tool_name': tool_name,
            'total_samples': total_samples,
            'samples_with_predictions': samples_with_predictions,
            'samples_without_predictions': total_samples - samples_with_predictions,
            'total_predictions': total_predictions,
            'avg_predictions_per_sample': avg_predictions_per_sample,
            'max_hop_distance': max_hop,
            'enriched_samples': enriched_samples,
            'hop_metrics': hop_metrics
        }
    
    def _print_model_report(self, tool_name: str, result: Dict) -> None:
        """Print formatted report for a tool"""
        print("\n" + "=" * 100)
        print(f"TOOL: {tool_name}")
        print("=" * 100)
        print(f"Total samples: {result['total_samples']}")
        print(f"Samples with predictions: {result['samples_with_predictions']}")
        print(f"Samples without predictions: {result['samples_without_predictions']}")
        print(f"Total predictions made: {result['total_predictions']}")
        print(f"Average predictions per sample: {result['avg_predictions_per_sample']:.2f}")
        print(f"Max hop distance observed: {result['max_hop_distance']}")
        print(f"Tolerance: {self.tolerance}")
        print("\n" + "-" * 100)
        print("HOP-BASED ACCURACY METRICS")
        print("-" * 100)
        print(f"{'Hop':<6} {'Perfect':<10} {'Accept':<10} {'Total FP':<10} "
              f"{'Samp w/ Perf':<15} {'Samp w/ Accept':<15} {'Samp w/ FP':<12} "
              f"{'Avg FP':<10}")
        print("-" * 100)
        
        hop_metrics = result['hop_metrics']
        for hop_level in sorted(hop_metrics.keys(), key=lambda x: int(x.split('_')[1])):
            metrics = hop_metrics[hop_level]
            hop_num = hop_level.split('_')[1]
            
            print(f"{hop_num:<6} "
                  f"{metrics['perfect_predictions']:<10} "
                  f"{metrics['acceptable_predictions']:<10} "
                  f"{metrics['false_positives']:<10} "
                  f"{metrics['samples_with_perfect']:<15} "
                  f"{metrics['samples_with_acceptable']:<15} "
                  f"{metrics['samples_with_fp']:<12} "
                  f"{metrics['avg_fp_per_sample']:.2f}")
        
        print("-" * 100)
        
        # Strict accuracy section
        print("\nSTRICT ACCURACY (Hop 0 only - exact match):")
        if 'hop_0' in hop_metrics:
            strict = hop_metrics['hop_0']
            print(f"  Samples with exact match: {strict['samples_with_perfect']}/{result['total_samples']} "
                  f"({strict['perfect_accuracy']*100:.2f}%)")
            print(f"  Total exact predictions: {strict['perfect_predictions']}")
            print(f"  Total false positives: {strict['false_positives']}")
            print(f"  Samples with zero FP: {strict['samples_with_zero_fp']}")
            print(f"  Average FP per sample: {strict['avg_fp_per_sample']:.2f}")
            if strict['fp_distribution']:
                print(f"  FP distribution: {strict['fp_distribution']}")
        
        # Show a few key hop levels in detail
        key_hops = [1, 3, 5]
        for hop in key_hops:
            hop_key = f'hop_{hop}'
            if hop_key in hop_metrics:
                metrics = hop_metrics[hop_key]
                print(f"\nHOP {hop} (tolerance={self.tolerance}, accept up to hop {hop + self.tolerance}):")
                print(f"  Perfect accuracy: {metrics['samples_with_perfect']}/{result['total_samples']} "
                      f"({metrics['perfect_accuracy']*100:.2f}%)")
                print(f"  Acceptable accuracy: {metrics['samples_with_acceptable']}/{result['total_samples']} "
                      f"({metrics['acceptable_accuracy']*100:.2f}%)")
                print(f"  Total FP: {metrics['false_positives']}")
                print(f"  Samples with FP: {metrics['samples_with_fp']}")
                print(f"  Average FP per sample: {metrics['avg_fp_per_sample']:.2f}")
        
        print("=" * 100 + "\n")


if __name__ == "__main__":
    tolerance = 3
    # Static tools
    static_path = "services/CodeSecurity/exp_dir_SVEN_python_1/SVEN_python_CodeQL_Semgrep.json"
    
    # llm
    llm_path = ("services/CodeSecurity/exp_dir_SVEN_python_1/"
                "SVEN_qwen2_5_coder_32b_mistral_latest_qwen2_5_coder_latest_"
                "llama3_1_latest_phi4_latest_deepseek_coder_6_7b_devstral_24b.json")
    
    # print("=" * 80)
    # print("STATIC TOOLS ANALYSIS (Tolerance=1)")
    # print("=" * 80)
    # static_analyser = AccuracyAnalysis(tool_type='static', result_path=static_path, tolerance=1)
    
    print("=" * 80)
    print(f"LLM TOOLS ANALYSIS (Tolerance={tolerance})")
    print("=" * 80)
    llm_analyser = AccuracyAnalysis(tool_type='llm', result_path=llm_path, tolerance=tolerance)