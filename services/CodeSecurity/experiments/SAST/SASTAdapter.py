import json
import re
from pathlib import Path
from typing import Optional


class SASTAdapter:
    """
    Adapter to transform SAST tool results into LLM-compatible format
    for ALPHA score calculation.
    """

    # Confidence priority: HIGH > MEDIUM > LOW > empty
    CONFIDENCE_PRIORITY = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, '': 0}


    def __init__(self, sast_json_path: str):
        """
        Initialise adapter with path to SAST results JSON.

        Args:
            sast_json_path: Path to SAST consolidated results JSON
        """
        self.sast_json_path = sast_json_path
        self.data = self._load_data()


    def _load_data(self) -> list:
        """Load SAST results JSON."""
        with open(self.sast_json_path, 'r') as f:
            return json.load(f)


    def _extract_cwe_id(self, cwe_value: str) -> Optional[str]:
        """
        Extract normalised CWE ID from various formats.

        Handles:
            - "CWE-079" -> "CWE-79"
            - "CWE-611: Improper Restriction..." -> "CWE-611"

        Returns:
            Normalised CWE string (e.g., "CWE-79") or None if invalid
        """
        if not cwe_value or not isinstance(cwe_value, str):
            return None

        match = re.search(r'CWE-0*(\d+)', cwe_value, re.IGNORECASE)
        if match:
            cwe_num = int(match.group(1))
            return f"CWE-{cwe_num}"

        return None


    def _get_cwes_from_finding(self, finding: dict) -> list:
        """
        Extract CWE IDs from a single finding.

        Returns:
            List of normalised CWE IDs
        """
        cwes_field = finding.get('cwes', [])
        result = []

        if isinstance(cwes_field, str):
            cwe_id = self._extract_cwe_id(cwes_field)
            if cwe_id:
                result.append(cwe_id)
        elif isinstance(cwes_field, list):
            for cwe_value in cwes_field:
                cwe_id = self._extract_cwe_id(cwe_value)
                if cwe_id:
                    result.append(cwe_id)

        return result


    def _get_unique_cwes_with_confidence(self, analysis_results: list) -> dict:
        """
        Extract unique CWEs with their highest confidence level.

        For each unique CWE, tracks the highest confidence it was reported with.

        Args:
            analysis_results: List of findings from a tool

        Returns:
            Dict mapping CWE -> highest confidence string
        """
        cwe_confidence = {}

        for finding in analysis_results:
            confidence = finding.get('confidence', '')
            if confidence:
                confidence = confidence.strip()

            finding_cwes = self._get_cwes_from_finding(finding)

            for cwe in finding_cwes:
                current_priority = self.CONFIDENCE_PRIORITY.get(confidence, 0)
                existing_priority = self.CONFIDENCE_PRIORITY.get(
                    cwe_confidence.get(cwe, ''), 0
                )

                if current_priority > existing_priority:
                    cwe_confidence[cwe] = confidence

        return cwe_confidence


    def _get_unique_cwes_ordered(self, analysis_results: list) -> list:
        """
        Extract unique CWEs preserving first occurrence order.

        Args:
            analysis_results: List of findings from a tool

        Returns:
            List of unique CWEs in order of first appearance
        """
        seen = set()
        ordered = []

        for finding in analysis_results:
            finding_cwes = self._get_cwes_from_finding(finding)
            for cwe in finding_cwes:
                if cwe not in seen:
                    seen.add(cwe)
                    ordered.append(cwe)

        return ordered


    def _normalise_ground_truth(self, true_label: str) -> str:
        """
        Normalise ground truth CWE format.

        Handles:
            - "CWE-020" -> "CWE-20"
            - "cwe-022" -> "CWE-22"
        """
        cwe_id = self._extract_cwe_id(true_label)
        return cwe_id if cwe_id else true_label


    def _select_by_confidence(
        self,
        unique_cwes_ordered: list,
        cwe_confidence: dict,
        tool: str
    ) -> Optional[str]:
        """
        Select single CWE based on confidence (Semgrep) or first (CodeQL).

        Args:
            unique_cwes_ordered: List of unique CWEs in order
            cwe_confidence: Dict mapping CWE -> confidence string
            tool: Tool name ("Semgrep" or "CodeQL")

        Returns:
            Selected CWE or None if empty
        """
        if not unique_cwes_ordered:
            return None

        if len(unique_cwes_ordered) == 1:
            return unique_cwes_ordered[0]

        # Multiple CWEs
        if tool == 'Semgrep':
            # Select by highest confidence
            max_priority = -1
            selected = None

            for cwe in unique_cwes_ordered:
                conf = cwe_confidence.get(cwe, '')
                priority = self.CONFIDENCE_PRIORITY.get(conf, 0)

                if priority > max_priority:
                    max_priority = priority
                    selected = cwe

            return selected
        else:
            # CodeQL: select first
            return unique_cwes_ordered[0]


    def transform(
        self,
        strategy: str = "confidence",
        output_path: Optional[str] = None
    ) -> list:
        """
        Transform SAST format to LLM-compatible format.

        Args:
            strategy: CWE selection strategy
                - "confidence": Select by confidence (Semgrep) or first (CodeQL)
                - "any_match": Use GT if present, otherwise fall back to confidence
            output_path: Optional path to save transformed JSON

        Returns:
            Transformed data in LLM format
        """
        if strategy not in ("confidence", "any_match"):
            raise ValueError(
                f"Invalid strategy: {strategy}. Use 'confidence' or 'any_match'"
            )

        transformed = []

        for sample in self.data:
            sample_index = sample['sample_index']
            true_label = sample['true_label']
            ground_truth = self._normalise_ground_truth(true_label)

            analysis_list = []

            for tool_analysis in sample['analysis']:
                tool_name = tool_analysis['tool']
                analysis_results = tool_analysis.get('analysis_results', [])

                # Extract unique CWEs with confidence and order
                cwe_confidence = self._get_unique_cwes_with_confidence(analysis_results)
                unique_cwes_ordered = self._get_unique_cwes_ordered(analysis_results)

                # Select final CWE based on strategy
                if strategy == "confidence":
                    selected_cwe = self._select_by_confidence(
                        unique_cwes_ordered,
                        cwe_confidence,
                        tool_name
                    )
                else:  # any_match
                    if ground_truth in unique_cwes_ordered:
                        selected_cwe = ground_truth
                    else:
                        # Fall back to confidence strategy
                        selected_cwe = self._select_by_confidence(
                            unique_cwes_ordered,
                            cwe_confidence,
                            tool_name
                        )

                # Build LLM-compatible analysis entry
                analysis_entry = {
                    'llm_model': tool_name,
                    'parsed_response': {
                        'cwe': [selected_cwe] if selected_cwe else []
                    },
                    '_original_cwes': unique_cwes_ordered,
                    '_cwe_confidence': cwe_confidence,
                    '_strategy': strategy
                }

                analysis_list.append(analysis_entry)

            transformed.append({
                'sample_index': sample_index,
                'true_label': true_label,
                'analysis': analysis_list
            })

        # Save if output path provided
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(transformed, f, indent=2)
            print(f"Saved transformed data ({strategy}) to {output_path}")

        return transformed


    def transform_both_strategies(self, output_dir: str) -> dict:
        """
        Transform using both strategies and save to separate files.

        Args:
            output_dir: Directory to save output files

        Returns:
            Dictionary with paths to both output files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        dataset_name = Path(self.sast_json_path).stem.split("_")[0]

        # Transform with 'confidence' strategy
        confidence_path = output_path / f"{dataset_name}_sast_transformed_confidence.json"
        self.transform(strategy="confidence", output_path=str(confidence_path))

        # Transform with 'any_match' strategy
        any_match_path = output_path / f"{dataset_name}_sast_transformed_any_match.json"
        self.transform(strategy="any_match", output_path=str(any_match_path))

        return {
            'confidence': str(confidence_path),
            'any_match': str(any_match_path)
        }


if __name__ == "__main__":
    # sast_path = "services/CodeSecurity/experiments/SAST/SecurityEval_consolidated_evaluation_results.json"
    sast_path = "services/CodeSecurity/experiments/SAST/SVEN_python_CodeQL_Semgrep.json"
    output_dir = "services/CodeSecurity/experiments/SAST"

    adapter = SASTAdapter(sast_path)
    paths = adapter.transform_both_strategies(output_dir)

    print(f"\nTransformed files:")
    print(f"  Confidence strategy: {paths['confidence']}")
    print(f"  Any-match strategy:  {paths['any_match']}")