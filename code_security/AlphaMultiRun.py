import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/..")

import json
from pathlib import Path
from typing import Callable, Optional
from collections import Counter


class ALPHAMultiRun:
    """
    ALPHA benchmark with support for multiple experimental runs
    and majority voting consensus.
    """

    def __init__(self, 
                 graph):
        """
        Initialise with a CWE graph instance.

        Args:
            graph: A BaseCWEGraph subclass instance (e.g., WeaknessCWEGraph)
        """
        self.graph = graph


    def _load_predictions(self, path: str) -> list:
        """Load predictions from a JSON file."""
        with open(path, 'r') as f:
            return json.load(f)


    def _extract_final_cwe(self, cwe_list: list) -> Optional[str]:
        """
        Extract the final CWE prediction from a list.

        Returns the last CWE in the list, or None if empty.
        """
        if not cwe_list:
            return None
        return cwe_list[-1]


    def _normalise_cwe(self, cwe: Optional[str]) -> Optional[str]:
        """
        Normalise CWE format for comparison.

        Handles variations like 'CWE-89', 'cwe-89', etc.
        Returns just the numeric part without 'CWE-' prefix.
        """
        if cwe is None:
            return None
        cwe = cwe.strip().upper()
        if cwe.startswith("CWE-"):
            cwe = cwe[4:]
        return cwe


    def _get_majority_prediction(self, predictions: list) -> Optional[str]:
        """
        Get majority prediction from a list of 3 predictions.

        Args:
            predictions: List of 3 CWE predictions (can contain None)

        Returns:
            Majority CWE if exists, otherwise first prediction (tiebreaker)
        """
        # Count occurrences
        counter = Counter(predictions)

        # Find most common
        most_common = counter.most_common()

        # Check for majority (at least 2 out of 3)
        if most_common[0][1] >= 2:
            return most_common[0][0]

        # No majority - use first prediction as tiebreaker
        return predictions[0]


    def _build_majority_predictions(self, runs: list) -> list:
        """
        Build majority predictions from multiple runs.

        Args:
            runs: List of 3 loaded prediction files (each is a list of samples)

        Returns:
            New predictions list with majority-voted CWE for each model
        """
        num_samples = len(runs[0])
        num_models = len(runs[0][0]['analysis'])

        # Get model names (order should be consistent across runs)
        model_names = [a['llm_model'] for a in runs[0][0]['analysis']]

        majority_predictions = []

        for sample_idx in range(num_samples):
            sample_index = runs[0][sample_idx]['sample_index']
            true_label = runs[0][sample_idx]['true_label']

            # Validate alignment across runs
            for run_idx, run in enumerate(runs):
                if run[sample_idx]['sample_index'] != sample_index:
                    raise ValueError(
                        f"Sample index mismatch at position {sample_idx}: "
                        f"Run 0 has {sample_index}, Run {run_idx} has {run[sample_idx]['sample_index']}"
                    )

            # Build majority for each model
            analysis_list = []

            for model_idx, model_name in enumerate(model_names):
                # Collect predictions across runs for this model
                preds_across_runs = []

                for run in runs:
                    model_analysis = run[sample_idx]['analysis'][model_idx]

                    # Validate model order is consistent
                    if model_analysis['llm_model'] != model_name:
                        raise ValueError(
                            f"Model order mismatch at sample {sample_idx}: "
                            f"Expected {model_name}, got {model_analysis['llm_model']}"
                        )

                    cwe_list = model_analysis['parsed_response']['cwe']
                    final_cwe = self._extract_final_cwe(cwe_list)
                    normalised = self._normalise_cwe(final_cwe)
                    preds_across_runs.append(normalised)

                # Get majority prediction
                majority_cwe = self._get_majority_prediction(preds_across_runs)

                # Format back to CWE-X format for consistency with get_alpha
                if majority_cwe is not None:
                    majority_cwe_formatted = f"CWE-{majority_cwe}"
                else:
                    majority_cwe_formatted = None

                # Create analysis entry matching original structure
                analysis_entry = {
                    'llm_model': model_name,
                    'parsed_response': {
                        'cwe': [majority_cwe_formatted] if majority_cwe_formatted else []
                    }
                }

                analysis_list.append(analysis_entry)

            majority_predictions.append({
                'sample_index': sample_index,
                'true_label': true_label,
                'analysis': analysis_list
            })

        return majority_predictions


    def get_alpha_multi_run(
        self,
        prediction_paths: list,
        gt_cwe_extraction_function: Callable,
        output_dir: str
    ) -> dict:
        """
        Calculate ALPHA scores for multiple runs and majority voting.

        Args:
            prediction_paths: List of 3 paths to prediction JSON files
            gt_cwe_extraction_function: Function to extract GT CWE from true_label
            output_dir: Directory to save all output files

        Returns:
            Dictionary with summary of all ALPHA scores
        """
        if len(prediction_paths) != 3:
            raise ValueError(f"Expected exactly 3 prediction paths, got {len(prediction_paths)}")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Load all runs
        runs = [self._load_predictions(path) for path in prediction_paths]

        # Validate sample counts match
        sample_counts = [len(run) for run in runs]
        if len(set(sample_counts)) != 1:
            raise ValueError(f"Sample count mismatch across runs: {sample_counts}")

        print(f"Loaded {len(runs)} runs with {sample_counts[0]} samples each")

        # Calculate ALPHA for each individual run
        individual_scores = {}

        for i, path in enumerate(prediction_paths, 1):
            print(f"\nCalculating ALPHA for Run {i}...")
            alpha_path = output_path / f"alpha_scores_run_{i}.json"
            detailed_path = output_path / f"detailed_results_run_{i}.json"

            self.graph.get_alpha(
                predictions_path=path,
                gt_cwe_extraction_function=gt_cwe_extraction_function,
                alpha_path=str(alpha_path),
                detailed_result_path=str(detailed_path)
            )

            # Load the scores for summary
            with open(alpha_path, 'r') as f:
                individual_scores[f'run_{i}'] = json.load(f)

        # Build majority predictions
        print("\nBuilding majority predictions...")
        majority_predictions = self._build_majority_predictions(runs)

        # Save majority predictions
        majority_pred_path = output_path / "majority_predictions.json"
        with open(majority_pred_path, 'w') as f:
            json.dump(majority_predictions, f, indent=2)
        print(f"Saved majority predictions to {majority_pred_path}")

        # Calculate ALPHA for majority predictions
        print("\nCalculating ALPHA for majority predictions...")
        self.graph.get_alpha(
            predictions_path=str(majority_pred_path),
            gt_cwe_extraction_function=gt_cwe_extraction_function,
            alpha_path=str(output_path / "alpha_scores_majority.json"),
            detailed_result_path=str(output_path / "detailed_results_majority.json")
        )

        # Load majority scores for summary
        with open(output_path / "alpha_scores_majority.json", 'r') as f:
            individual_scores['majority'] = json.load(f)

        # Create summary
        summary = {
            'individual_runs': individual_scores,
            'num_samples': sample_counts[0],
            'num_models': len(runs[0][0]['analysis']),
            'output_dir': str(output_dir)
        }

        # Save summary
        summary_path = output_path / "alpha_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"\nSaved summary to {summary_path}")

        return summary