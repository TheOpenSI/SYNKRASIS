import json
import re
from collections import Counter
from typing import Optional


class SASTEDA:
    """
    Exploratory Data Analysis for SAST tool results.
    """

    def __init__(self, json_path: str):
        """
        Initialise EDA with path to SAST results JSON.

        Args:
            json_path: Path to consolidated SAST results JSON
        """
        self.json_path = json_path
        self.data = self._load_data()
        self.tools = self._get_tools()


    def _load_data(self) -> list:
        """Load SAST results JSON."""
        with open(self.json_path, 'r') as f:
            return json.load(f)


    def _get_tools(self) -> list:
        """Extract tool names from data."""
        if not self.data:
            return []
        return [t['tool'] for t in self.data[0]['analysis']]


    def _extract_cwe_id(self, cwe_value: str) -> Optional[str]:
        """
        Extract normalised CWE ID from various formats.

        Handles:
            - "CWE-079" -> "CWE-79"
            - "CWE-611: Description" -> "CWE-611"
        """
        if not cwe_value or not isinstance(cwe_value, str):
            return None
        match = re.search(r'CWE-0*(\d+)', cwe_value, re.IGNORECASE)
        if match:
            return f"CWE-{int(match.group(1))}"
        return None


    def _get_unique_cwes_from_results(self, analysis_results: list) -> list:
        """
        Extract UNIQUE CWE IDs from a tool's analysis results.

        Removes duplicates (e.g., Semgrep reporting same CWE multiple times).
        """
        all_cwes = []
        for finding in analysis_results:
            cwes = finding.get('cwes', [])
            if isinstance(cwes, str):
                cwe_id = self._extract_cwe_id(cwes)
                if cwe_id:
                    all_cwes.append(cwe_id)
            elif isinstance(cwes, list):
                for cwe in cwes:
                    cwe_id = self._extract_cwe_id(cwe)
                    if cwe_id:
                        all_cwes.append(cwe_id)
        # Return unique CWEs
        return list(set(all_cwes))


    def get_tool_stats(self, tool: str) -> dict:
        """
        Get comprehensive statistics for a single tool.

        Returns:
            Dictionary with:
                - predicted_something: count
                - predicted_nothing: count
                - correct_any_match: count
                - cwe_count_distribution: Counter
        """
        total_samples = len(self.data)
        predicted_something = 0
        predicted_nothing = 0
        correct_any_match = 0
        cwe_count_distribution = Counter()

        for sample in self.data:
            gt = self._extract_cwe_id(sample['true_label'])

            for tool_analysis in sample['analysis']:
                if tool_analysis['tool'] != tool:
                    continue

                results = tool_analysis.get('analysis_results', [])
                unique_cwes = self._get_unique_cwes_from_results(results)
                num_unique = len(unique_cwes)

                cwe_count_distribution[num_unique] += 1

                if num_unique > 0:
                    predicted_something += 1
                    if gt in unique_cwes:
                        correct_any_match += 1
                else:
                    predicted_nothing += 1

        return {
            'total_samples': total_samples,
            'predicted_something': predicted_something,
            'predicted_nothing': predicted_nothing,
            'correct_any_match': correct_any_match,
            'cwe_count_distribution': cwe_count_distribution
        }


    def get_semgrep_confidence_stats(self) -> dict:
        """
        Get Semgrep confidence statistics.

        Returns:
            Dictionary with:
                - total_findings: count
                - findings_with_confidence: count
                - samples_with_at_least_one_confidence: count
                - confidence_values: Counter
        """
        total_findings = 0
        findings_with_confidence = 0
        samples_with_at_least_one_confidence = 0
        confidence_values = Counter()

        for sample in self.data:
            for tool_analysis in sample['analysis']:
                if tool_analysis['tool'] != 'Semgrep':
                    continue

                results = tool_analysis.get('analysis_results', [])
                sample_has_confidence = False

                for finding in results:
                    total_findings += 1
                    confidence = finding.get('confidence', '')

                    if confidence and confidence.strip():
                        findings_with_confidence += 1
                        confidence_values[confidence.strip()] += 1
                        sample_has_confidence = True

                if sample_has_confidence:
                    samples_with_at_least_one_confidence += 1

        return {
            'total_findings': total_findings,
            'findings_with_confidence': findings_with_confidence,
            'samples_with_at_least_one_confidence': samples_with_at_least_one_confidence,
            'confidence_values': confidence_values
        }


    def print_report(self) -> None:
        """Print clean EDA report."""
        total_samples = len(self.data)

        print(f"Total samples: {total_samples}")

        for tool in self.tools:
            print("\n" + "=" * 60)
            print(f"TOOL: {tool}")
            print("=" * 60)

            stats = self.get_tool_stats(tool)

            pred = stats['predicted_something']
            no_pred = stats['predicted_nothing']
            correct = stats['correct_any_match']

            print(f"\nPrediction Summary:")
            print(f"  Predicted something: {pred} ({100*pred/total_samples:.1f}%)")
            print(f"  Predicted nothing:   {no_pred} ({100*no_pred/total_samples:.1f}%)")

            print(f"\nUnique CWEs Reported (distribution):")
            for num_cwes in sorted(stats['cwe_count_distribution'].keys()):
                count = stats['cwe_count_distribution'][num_cwes]
                print(f"  {num_cwes} CWE(s): {count} samples ({100*count/total_samples:.1f}%)")

            print(f"\nAccuracy (any_match - GT in reported CWEs):")
            if pred > 0:
                print(f"  Correct (of predicted): {correct}/{pred} ({100*correct/pred:.1f}%)")
            print(f"  Correct (of all):       {correct}/{total_samples} ({100*correct/total_samples:.1f}%)")

            # Semgrep-specific
            if tool == 'Semgrep':
                semgrep_stats = self.get_semgrep_confidence_stats()
                total_findings = semgrep_stats['total_findings']

                if total_findings > 0:
                    print(f"\nSemgrep Confidence:")
                    print(f"  Total findings: {total_findings}")
                    print(f"  Findings with confidence: {semgrep_stats['findings_with_confidence']} ({100*semgrep_stats['findings_with_confidence']/total_findings:.1f}%)")
                    print(f"  Samples with at least 1 confidence: {semgrep_stats['samples_with_at_least_one_confidence']} ({100*semgrep_stats['samples_with_at_least_one_confidence']/total_samples:.1f}%)")

                    print(f"\n  Confidence values:")
                    for value, count in semgrep_stats['confidence_values'].most_common():
                        print(f"    {value}: {count}")


if __name__ == "__main__":
    sec_eval = "services/CodeSecurity/experiments/SAST/SecurityEval_consolidated_evaluation_results.json"
    sven_path = "services/CodeSecurity/experiments/SAST/SVEN_python_CodeQL_Semgrep.json"

    eda = SASTEDA(sven_path)
    eda.print_report()