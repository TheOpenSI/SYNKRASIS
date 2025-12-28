import sys
import json
import numpy as np
from pathlib import Path


class ALPHAResultsTable:
    """
    Generates LaTeX tables for ALPHA benchmark results.
    """

    # Model display names (cleaner for paper)
    MODEL_DISPLAY_NAMES = {
        'qwen2.5-coder:32b': 'Qwen2.5-Coder-32B',
        'qwen2.5-coder:latest': 'Qwen2.5-Coder-7B',
        'mistral:latest': 'Mistral-7B',
        'llama3.1:latest': 'Llama3.1-8B',
        'phi4:latest': 'Phi4-14B',
        'deepseek-coder:6.7b': 'DeepSeek-Coder-6.7B',
        'devstral:24b': 'Devstral-24B',
        'CodeQL': 'CodeQL',
        'Semgrep': 'Semgrep'
    }


    def __init__(self):
        """Initialise the table generator."""
        self.llm_results = {}  # {dataset: {model: {'mean': x, 'std': y}}}
        self.sast_results = {}  # {dataset: {tool: {'confidence': x, 'any_match': y}}}


    def _load_json(self, path: str) -> dict:
        """Load JSON file."""
        with open(path, 'r') as f:
            return json.load(f)


    def _calc_llm_stats(self, summary: dict) -> dict:
        """
        Calculate mean and std for each LLM across runs.

        Args:
            summary: Multi-run summary dict with 'individual_runs'

        Returns:
            Dict mapping model -> {'mean': x, 'std': y}
        """
        runs = summary['individual_runs']
        stats = {}

        # Get models from run_1
        models = list(runs['run_1'].keys())

        for model in models:
            values = [
                runs['run_1'][model],
                runs['run_2'][model],
                runs['run_3'][model]
            ]
            stats[model] = {
                'mean': np.mean(values),
                'std': np.std(values, ddof=1)
            }

        return stats


    def load_llm_results(self, dataset_name: str, summary_path: str) -> None:
        """
        Load LLM multi-run results for a dataset.

        Args:
            dataset_name: Name of dataset (e.g., 'SVEN', 'SecurityEval')
            summary_path: Path to alpha_summary.json
        """
        summary = self._load_json(summary_path)
        self.llm_results[dataset_name] = self._calc_llm_stats(summary)


    def load_sast_results(
        self,
        dataset_name: str,
        confidence_path: str,
        any_match_path: str
    ) -> None:
        """
        Load SAST results for a dataset.

        Args:
            dataset_name: Name of dataset
            confidence_path: Path to confidence strategy results
            any_match_path: Path to any_match strategy results
        """
        conf_data = self._load_json(confidence_path)
        any_data = self._load_json(any_match_path)

        self.sast_results[dataset_name] = {}

        for tool in conf_data.keys():
            self.sast_results[dataset_name][tool] = {
                'confidence': conf_data[tool],
                'any_match': any_data[tool]
            }


    def _escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters."""
        return text.replace('_', '\\_').replace('-', '-')


    def _get_display_name(self, model: str) -> str:
        """Get clean display name for a model."""
        return self.MODEL_DISPLAY_NAMES.get(model, model)


    def generate_latex_table(
        self,
        datasets: list,
        caption: str = None,
        label: str = None,
        normalise: bool = False,
        num_samples: dict = None
    ) -> str:
        """
        Generate LaTeX table with all results.

        Args:
            datasets: List of dataset names to include
            caption: Table caption
            label: Table label
            normalise: If True, divide scores by num_samples
            num_samples: Dict mapping dataset -> sample count (for normalisation)

        Returns:
            LaTeX table string
        """
        # Determine number of columns
        num_datasets = len(datasets)

        # Build column spec
        col_spec = 'l' + 'r' * num_datasets

        lines = [
            '\\begin{table}[htbp]',
            '    \\centering',
        ]

        if caption:
            lines.append(f'    \\caption{{{caption}}}')

        if label:
            lines.append(f'    \\label{{{label}}}')

        lines.extend([
            f'    \\begin{{tabular}}{{{col_spec}}}',
            '        \\toprule',
        ])

        # Header row
        header = '        Model & ' + ' & '.join(datasets) + ' \\\\'
        lines.append(header)
        lines.append('        \\midrule')

        # LLM rows
        if self.llm_results:
            # Get all LLM models (from first dataset)
            first_dataset = list(self.llm_results.keys())[0]
            llm_models = list(self.llm_results[first_dataset].keys())

            for model in llm_models:
                display_name = self._get_display_name(model)
                row_values = []

                for dataset in datasets:
                    if dataset in self.llm_results and model in self.llm_results[dataset]:
                        stats = self.llm_results[dataset][model]
                        mean = stats['mean']
                        std = stats['std']

                        if normalise and num_samples and dataset in num_samples:
                            mean = mean / num_samples[dataset]
                            std = std / num_samples[dataset]
                            row_values.append(f'{mean:.2f} $\\pm$ {std:.2f}')
                        else:
                            row_values.append(f'{mean:.1f} $\\pm$ {std:.1f}')
                    else:
                        row_values.append('--')

                row = f'        {display_name} & ' + ' & '.join(row_values) + ' \\\\'
                lines.append(row)

        # Separator before SAST
        if self.sast_results:
            lines.append('        \\midrule')
            lines.append('        \\multicolumn{' + str(num_datasets + 1) + '}{l}{\\textit{SAST Tools (confidence / any\\_match)}} \\\\')
            lines.append('        \\midrule')

            # SAST rows
            first_dataset = list(self.sast_results.keys())[0]
            sast_tools = list(self.sast_results[first_dataset].keys())

            for tool in sast_tools:
                display_name = self._get_display_name(tool)
                row_values = []

                for dataset in datasets:
                    if dataset in self.sast_results and tool in self.sast_results[dataset]:
                        data = self.sast_results[dataset][tool]
                        conf = data['confidence']
                        any_m = data['any_match']

                        if normalise and num_samples and dataset in num_samples:
                            conf = conf / num_samples[dataset]
                            any_m = any_m / num_samples[dataset]
                            row_values.append(f'{conf:.2f} / {any_m:.2f}')
                        else:
                            row_values.append(f'{conf:.1f} / {any_m:.1f}')
                    else:
                        row_values.append('--')

                row = f'        {display_name} & ' + ' & '.join(row_values) + ' \\\\'
                lines.append(row)

        lines.extend([
            '        \\bottomrule',
            '    \\end{tabular}',
            '\\end{table}'
        ])

        return '\n'.join(lines)


    def generate_separate_tables(
        self,
        datasets: list,
        num_samples: dict = None,
        normalise: bool = False
    ) -> dict:
        """
        Generate separate tables for LLMs and SAST tools.

        Returns:
            Dict with 'llm' and 'sast' table strings
        """
        tables = {}

        # LLM table
        num_datasets = len(datasets)
        col_spec = 'l' + 'r' * num_datasets

        llm_lines = [
            '\\begin{table}[htbp]',
            '    \\centering',
            '    \\caption{ALPHA scores for LLMs across datasets (mean $\\pm$ std over 3 runs)}',
            '    \\label{tab:alpha_llm}',
            f'    \\begin{{tabular}}{{{col_spec}}}',
            '        \\toprule',
            '        Model & ' + ' & '.join(datasets) + ' \\\\',
            '        \\midrule',
        ]

        if self.llm_results:
            first_dataset = list(self.llm_results.keys())[0]
            llm_models = list(self.llm_results[first_dataset].keys())

            for model in llm_models:
                display_name = self._get_display_name(model)
                row_values = []

                for dataset in datasets:
                    if dataset in self.llm_results and model in self.llm_results[dataset]:
                        stats = self.llm_results[dataset][model]
                        mean = stats['mean']
                        std = stats['std']

                        if normalise and num_samples and dataset in num_samples:
                            mean = mean / num_samples[dataset]
                            std = std / num_samples[dataset]
                            row_values.append(f'{mean:.2f} $\\pm$ {std:.2f}')
                        else:
                            row_values.append(f'{mean:.1f} $\\pm$ {std:.1f}')
                    else:
                        row_values.append('--')

                row = f'        {display_name} & ' + ' & '.join(row_values) + ' \\\\'
                llm_lines.append(row)

        llm_lines.extend([
            '        \\bottomrule',
            '    \\end{tabular}',
            '\\end{table}'
        ])

        tables['llm'] = '\n'.join(llm_lines)

        # SAST table
        sast_lines = [
            '\\begin{table}[htbp]',
            '    \\centering',
            '    \\caption{ALPHA scores for SAST tools across datasets}',
            '    \\label{tab:alpha_sast}',
            '    \\begin{tabular}{lrrrr}',
            '        \\toprule',
        ]

        # Header with sub-columns for confidence and any_match
        sast_lines.append('        & \\multicolumn{2}{c}{SVEN} & \\multicolumn{2}{c}{SecurityEval} \\\\')
        sast_lines.append('        \\cmidrule(lr){2-3} \\cmidrule(lr){4-5}')
        sast_lines.append('        Tool & Conf. & Any & Conf. & Any \\\\')
        sast_lines.append('        \\midrule')

        if self.sast_results:
            first_dataset = list(self.sast_results.keys())[0]
            sast_tools = list(self.sast_results[first_dataset].keys())

            for tool in sast_tools:
                display_name = self._get_display_name(tool)
                row_values = []

                for dataset in datasets:
                    if dataset in self.sast_results and tool in self.sast_results[dataset]:
                        data = self.sast_results[dataset][tool]
                        conf = data['confidence']
                        any_m = data['any_match']

                        if normalise and num_samples and dataset in num_samples:
                            conf = conf / num_samples[dataset]
                            any_m = any_m / num_samples[dataset]
                            row_values.extend([f'{conf:.2f}', f'{any_m:.2f}'])
                        else:
                            row_values.extend([f'{conf:.1f}', f'{any_m:.1f}'])
                    else:
                        row_values.extend(['--', '--'])

                row = f'        {display_name} & ' + ' & '.join(row_values) + ' \\\\'
                sast_lines.append(row)

        sast_lines.extend([
            '        \\bottomrule',
            '    \\end{tabular}',
            '\\end{table}'
        ])

        tables['sast'] = '\n'.join(sast_lines)

        return tables


    def load_all_from_directory(self, base_path: str) -> None:
        """
        Load all results from the standard directory structure.

        Expected structure:
            base_path/
            ├── sast_security_eval/
            │   └── sast_security_eval.json
            ├── sast_security_eval_any/
            │   └── sast_security_eval_any.json
            ├── sast_sven/
            │   └── sast_sven.json
            ├── sast_sven_any/
            │   └── sast_sven_any.json
            ├── security_eval_multi_run/
            │   └── alpha_summary.json
            └── sven_multi_run/
                └── alpha_summary.json

        Args:
            base_path: Path to the alpha_results directory
        """
        base = Path(base_path)

        # Load LLM results
        sven_summary = base / 'sven_multi_run' / 'alpha_summary.json'
        seceval_summary = base / 'security_eval_multi_run' / 'alpha_summary.json'

        if sven_summary.exists():
            self.load_llm_results('SVEN', str(sven_summary))
            print(f"Loaded SVEN LLM results from {sven_summary}")
        else:
            print(f"Warning: {sven_summary} not found")

        if seceval_summary.exists():
            self.load_llm_results('SecurityEval', str(seceval_summary))
            print(f"Loaded SecurityEval LLM results from {seceval_summary}")
        else:
            print(f"Warning: {seceval_summary} not found")

        # Load SAST results
        sast_sven_conf = base / 'sast_sven' / 'sast_sven.json'
        sast_sven_any = base / 'sast_sven_any' / 'sast_sven_any.json'
        sast_seceval_conf = base / 'sast_security_eval' / 'sast_security_eval.json'
        sast_seceval_any = base / 'sast_security_eval_any' / 'sast_security_eval_any.json'

        if sast_sven_conf.exists() and sast_sven_any.exists():
            self.load_sast_results('SVEN', str(sast_sven_conf), str(sast_sven_any))
            print(f"Loaded SVEN SAST results")
        else:
            print(f"Warning: SVEN SAST files not found")

        if sast_seceval_conf.exists() and sast_seceval_any.exists():
            self.load_sast_results('SecurityEval', str(sast_seceval_conf), str(sast_seceval_any))
            print(f"Loaded SecurityEval SAST results")
        else:
            print(f"Warning: SecurityEval SAST files not found")


if __name__ == "__main__":
    # Default path
    base_path = "code_security/alpha_results"

    if len(sys.argv) > 1:
        base_path = sys.argv[1]

    print(f"Loading results from: {base_path}")
    print("=" * 60)

    generator = ALPHAResultsTable()
    generator.load_all_from_directory(base_path)

    print("\n" + "=" * 60)
    print("GENERATING TABLES")
    print("=" * 60)

    # Generate combined table
    print("\n--- Combined Table ---\n")
    latex = generator.generate_latex_table(
        datasets=['SVEN', 'SecurityEval'],
        caption='ALPHA scores for vulnerability detection across datasets. Lower scores indicate better performance. LLM results show mean $\\pm$ standard deviation across 3 runs. SAST results show confidence-based / any-match selection strategies.',
        label='tab:alpha_results'
    )
    print(latex)

    # Generate separate tables
    print("\n\n--- Separate Tables ---\n")
    tables = generator.generate_separate_tables(
        datasets=['SVEN', 'SecurityEval']
    )
    print("LLM Table:")
    print(tables['llm'])
    print("\nSAST Table:")
    print(tables['sast'])