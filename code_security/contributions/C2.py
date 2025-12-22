import json
from collections import defaultdict
import sys
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np


class ConsistencyAnalyser:
    """
    Analyses consistency of LLM vulnerability predictions across multiple runs.
    
    This class loads experimental results from multiple JSON files and calculates
    agreement metrics (Perfect Agreement and Majority Agreement) for each LLM model.
    """
    
    def __init__(self, json_paths: list[str]):
        """
        Initialise the analyser with paths to experimental result files.
        
        Args:
            json_paths: List of paths to JSON files (one per experimental run).
                        Expects exactly 3 files for 3-run consistency analysis.
        
        Raises:
            ValueError: If number of paths is not exactly 3.
        """
        if len(json_paths) != 3:
            raise ValueError(f"Expected exactly 3 JSON paths, got {len(json_paths)}")
        
        self.json_paths = json_paths
        self.runs = []
        self.models = []
        self.predictions = {}
        
        self._load_all_runs()
        self._extract_predictions()


    def _load_json(self, path: str) -> list[dict]:
        """Load a single JSON file and return its contents."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)


    def _load_all_runs(self) -> None:
        """Load all experimental runs and validate sample alignment."""
        for path in self.json_paths:
            run_data = self._load_json(path)
            self.runs.append(run_data)
        
        # Validate that all runs have the same samples
        sample_counts = [len(run) for run in self.runs]
        if len(set(sample_counts)) != 1:
            raise ValueError(
                f"Sample count mismatch across runs: {sample_counts}. "
                "All runs must have the same number of samples."
            )
        
        # Validate sample indices align
        for sample_idx in range(len(self.runs[0])):
            indices = [run[sample_idx]["sample_index"] for run in self.runs]
            if len(set(indices)) != 1:
                raise ValueError(
                    f"Sample index mismatch at position {sample_idx}: {indices}. "
                    "Samples must be in the same order across all runs."
                )
        
        # Extract model names from first sample of first run
        self.models = [
            analysis["llm_model"] 
            for analysis in self.runs[0][0]["analysis"]
        ]


    def _normalise_cwe(self, cwe: str) -> str:
        """
        Normalise CWE identifier for consistent comparison.
        
        Handles case differences and strips whitespace.
        
        Args:
            cwe: Raw CWE string (e.g., "CWE-89", "cwe-89")
        
        Returns:
            Normalised CWE string in uppercase (e.g., "CWE-89")
        """
        return cwe.strip().upper()


    def _get_final_cwe(self, cwe_list: list[str]) -> Optional[str]:
        """
        Extract the final CWE prediction from a list.
        
        Args:
            cwe_list: List of CWE predictions from parsed_response
        
        Returns:
            The last CWE in the list (normalised), or None if list is empty
        """
        if not cwe_list:
            return None
        return self._normalise_cwe(cwe_list[-1])


    def _extract_predictions(self) -> None:
        """
        Build the intermediate data structure mapping models to predictions.
        
        Creates a nested dict structure:
        {
            "model_name": {
                sample_index: [run1_pred, run2_pred, run3_pred],
                ...
            },
            ...
        }
        """
        self.predictions = {model: {} for model in self.models}
        
        num_samples = len(self.runs[0])
        
        for sample_idx in range(num_samples):
            sample_index = self.runs[0][sample_idx]["sample_index"]
            
            for model in self.models:
                preds_across_runs = []
                
                for run in self.runs:
                    sample = run[sample_idx]
                    
                    # Find the analysis entry for this model
                    model_analysis = None
                    for analysis in sample["analysis"]:
                        if analysis["llm_model"] == model:
                            model_analysis = analysis
                            break
                    
                    if model_analysis is None:
                        raise ValueError(
                            f"Model '{model}' not found in sample {sample_index}. "
                            "All models must be present in all samples across all runs."
                        )
                    
                    cwe_list = model_analysis["parsed_response"]["cwe"]
                    final_cwe = self._get_final_cwe(cwe_list)
                    preds_across_runs.append(final_cwe)
                
                self.predictions[model][sample_index] = preds_across_runs


    def calculate_agreement(self) -> dict:
        """
        Calculate agreement metrics for each model.
        
        Returns:
            Dictionary mapping model names to their metrics:
            {
                "model_name": {
                    "total_samples": int,
                    "perfect_agreement_count": int,
                    "majority_agreement_count": int,
                    "perfect_agreement_pct": float,
                    "majority_agreement_pct": float
                },
                ...
            }
        """
        results = {}
        
        for model in self.models:
            model_preds = self.predictions[model]
            total = len(model_preds)
            perfect_count = 0
            majority_count = 0
            
            for sample_idx, preds in model_preds.items():
                # Perfect agreement: all 3 predictions are identical
                if preds[0] == preds[1] == preds[2]:
                    perfect_count += 1
                    majority_count += 1  # Perfect implies majority
                # Majority agreement: at least 2 out of 3 are identical
                elif (preds[0] == preds[1] or 
                      preds[0] == preds[2] or 
                      preds[1] == preds[2]):
                    majority_count += 1
            
            results[model] = {
                "total_samples": total,
                "perfect_agreement_count": perfect_count,
                "majority_agreement_count": majority_count,
                "perfect_agreement_pct": (perfect_count / total) * 100 if total > 0 else 0,
                "majority_agreement_pct": (majority_count / total) * 100 if total > 0 else 0
            }
        
        return results


    def generate_latex_table(self, caption: str = None, label: str = None) -> str:
        """
        Generate a LaTeX table of consistency results.
        
        Args:
            caption: Optional table caption
            label: Optional table label for referencing
        
        Returns:
            LaTeX formatted table string
        """
        results = self.calculate_agreement()
        
        # Escape underscores in model names for LaTeX
        def escape_latex(text: str) -> str:
            return text.replace("_", "\\_")
        
        # Build table rows
        rows = []
        for model in self.models:
            metrics = results[model]
            model_escaped = escape_latex(model)
            rows.append(
                f"        {model_escaped} & "
                # f"{metrics['total_samples']} & "
                f"{metrics['perfect_agreement_pct']:.2f} & "
                f"{metrics['majority_agreement_pct']:.2f} \\\\"
            )
        
        # Construct full table
        table_lines = [
            "\\begin{table}[htbp]",
            "    \\centering",
        ]
        
        if caption:
            table_lines.append(f"    \\caption{{{caption}}}")
        
        if label:
            table_lines.append(f"    \\label{{{label}}}")
        
        table_lines.extend([
            "    \\begin{tabular}{lrr}",
            "        \\toprule",
            "        Model & Perfect Agreement (\\%) & Majority Agreement (\\%) \\\\",
            "        \\midrule",
        ])
        
        table_lines.extend(rows)
        
        table_lines.extend([
            "        \\bottomrule",
            "    \\end{tabular}",
            "\\end{table}",
        ])
        
        return "\n".join(table_lines)
    
    
    def generate_consistency_dot_plot(
        self, 
        sven_results: dict,
        securityeval_results: dict,
        output_path: str = "consistency_dot_plot.pdf",
    ) -> None:
        """
        Generate a dot plot comparing LLM consistency across two datasets.
        
        Args:
            sven_results: Dict mapping model names to Perfect Agreement % for SVEN
            securityeval_results: Dict mapping model names to Perfect Agreement % for SecurityEval
            output_path: Path to save the figure (supports .pdf, .png, .svg)
        """
        # Set up the style for academic papers
        plt.rcParams.update({
            'font.family': 'serif',
            'font.size': 10,
            'axes.labelsize': 11,
            'axes.titlesize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10,
            'figure.dpi': 300,
        })
        
        # Get models and sort by SVEN performance (highest at top)
        models = list(sven_results.keys())
        models_sorted = sorted(models, key=lambda m: securityeval_results[m], reverse=False)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(8, 5))
        
        # Y positions for each model
        y_positions = np.arange(len(models_sorted))
        
        # Colours
        sven_colour = "#000000"       # Black
        seceval_colour = "#FFFFFF"    # White
        line_colour = "#0A0A0A"       # black
        
        # Plot connecting lines first (so dots appear on top)
        for i, model in enumerate(models_sorted):
            sven_val = sven_results[model]
            seceval_val = securityeval_results[model]
            ax.plot(
                [sven_val, seceval_val], 
                [i, i], 
                color=line_colour, 
                linewidth=1.5, 
                zorder=1
            )
        
        # Plot dots for SVEN
        sven_values = [sven_results[m] for m in models_sorted]
        ax.scatter(
            sven_values, 
            y_positions, 
            color=sven_colour, 
            s=100, 
            zorder=2, 
            label='SVEN',
            edgecolors=line_colour,
            linewidths=0.5
        )
        
        # Plot dots for SecurityEval
        seceval_values = [securityeval_results[m] for m in models_sorted]
        ax.scatter(
            seceval_values, 
            y_positions, 
            color=seceval_colour, 
            s=100, 
            zorder=2, 
            label='SecurityEval',
            edgecolors=line_colour,
            linewidths=0.5
        )
        
        # Customise axes
        ax.set_yticks(y_positions)
        ax.set_yticklabels(models_sorted)
        ax.set_xlabel('Perfect Agreement (%)')
        ax.set_xlim(0, 100)
        
        # Add vertical grid lines
        ax.xaxis.grid(True, linestyle='--', alpha=0.7)
        ax.set_axisbelow(True)
        
        # Remove top and right spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Add legend
        ax.legend(loc='lower right', frameon=True, fancybox=False, edgecolor='black')
        
        # Tight layout
        plt.tight_layout()
        
        # Save figure
        plt.savefig(output_path, bbox_inches='tight', dpi=300)
        plt.close()



if __name__ == "__main__":
    # SVEN
    # e_1 = ("services/CodeSecurity/experiments/exp_dir_SVEN_python_1/SVEN_python_qwen2_5_coder_32b_"
    # "python_mistral_latest_python_qwen2_5_coder_latest_python_llama3_1_latest_"
    # "python_phi4_latest_python_deepseek_coder_6_7b_python_devstral_24b.json")
    # e_2 = ("services/CodeSecurity/experiments/exp_dir_SVEN_python_2/SVEN_python_qwen2_5_coder_32b_"
    # "python_mistral_latest_python_qwen2_5_coder_latest_python_llama3_1_latest_"
    # "python_phi4_latest_python_deepseek_coder_6_7b_python_devstral_24b.json")
    # e_3 = ("services/CodeSecurity/experiments/exp_dir_SVEN_python_3/SVEN_python_qwen2_5_coder_32b_"
    # "python_mistral_latest_python_qwen2_5_coder_latest_python_llama3_1_latest_"
    # "python_phi4_latest_python_deepseek_coder_6_7b_python_devstral_24b.json")
    
    # SecurityEval
    e_1 = ("services/CodeSecurity/experiments/exp_dir_SecurityEval_1/SecurityEval_qwen2_5_coder_32b_"
    "mistral_latest_qwen2_5_coder_latest_llama3_1_latest_"
    "phi4_latest_deepseek_coder_6_7b_devstral_24b.json")
    e_2 = ("services/CodeSecurity/experiments/exp_dir_SecurityEval_2/SecurityEval_qwen2_5_coder_32b_"
    "mistral_latest_qwen2_5_coder_latest_llama3_1_latest_"
    "phi4_latest_deepseek_coder_6_7b_devstral_24b.json")
    e_3 = ("services/CodeSecurity/experiments/exp_dir_SecurityEval_3/SecurityEval_qwen2_5_coder_32b_"
    "mistral_latest_qwen2_5_coder_latest_llama3_1_latest_"
    "phi4_latest_deepseek_coder_6_7b_devstral_24b.json")
    
    analyser = ConsistencyAnalyser([e_1, e_2, e_3])
    
    print("=== Consistency Analysis Results ===\n")
    
    results = analyser.calculate_agreement()
    for model, metrics in results.items():
        print(f"{model}:")
        print(f"  Samples: {metrics['total_samples']}")
        print(f"  Perfect Agreement: {metrics['perfect_agreement_pct']:.2f}%")
        print(f"  Majority Agreement: {metrics['majority_agreement_pct']:.2f}%")
        print()
    
    print("\n=== LaTeX Table ===\n")
    print(analyser.generate_latex_table(
        caption="LLM prediction consistency across three experimental runs",
        label="tab:consistency"
    ))
    
    # plot
    sven_results = {
        'qwen2.5-coder:32b': 81.87,
        'mistral:7b': 63.74,
        'qwen2.5-coder:7b': 71.64,
        'llama3.1:8b': 50.88,
        'phi4:14b': 66.96,
        'deepseek-coder:6.7b': 23.98,
        'devstral:24b': 73.39,
    }

    securityeval_results = {
        'qwen2.5-coder:32b': 61.98,
        'mistral:7b': 20.66,
        'qwen2.5-coder:7b': 21.49,
        'llama3.1:8b': 16.53,
        'phi4:14b': 34.71,
        'deepseek-coder:6.7b': 8.26,
        'devstral:24b': 52.07,
    }

    analyser.generate_consistency_dot_plot(
        sven_results,
        securityeval_results,
        output_path='code_security/contributions/c2.png'
    )    