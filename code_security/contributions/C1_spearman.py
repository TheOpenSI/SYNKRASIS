"""
ALPHA Correlation Analysis

Computes Spearman correlation statistics for ALPHA scores
across SVEN and SecurityEval datasets.
"""

from scipy import stats
import numpy as np


def compute_alpha_correlations(
    llm_data: dict,
    sast_data: dict,
    sven_samples: int = 342,
    seceval_samples: int = 121,
    normalise: bool = True
) -> dict:
    """
    Compute Spearman correlation statistics for ALPHA scores.

    Args:
        llm_data: Dict mapping model name -> {'sven': score, 'seceval': score}
        sast_data: Dict mapping tool name -> {'sven': score, 'seceval': score}
        sven_samples: Number of samples in SVEN dataset
        seceval_samples: Number of samples in SecurityEval dataset
        normalise: If True, divide scores by sample count

    Returns:
        Dict with correlation statistics for all groups
    """
    # Normalise if requested
    if normalise:
        llm_norm = {k: {'sven': v['sven']/sven_samples, 
                        'seceval': v['seceval']/seceval_samples} 
                    for k, v in llm_data.items()}
        sast_norm = {k: {'sven': v['sven']/sven_samples, 
                         'seceval': v['seceval']/seceval_samples} 
                     for k, v in sast_data.items()}
    else:
        llm_norm = llm_data
        sast_norm = sast_data

    # Extract values
    llm_sven = [v['sven'] for v in llm_norm.values()]
    llm_seceval = [v['seceval'] for v in llm_norm.values()]
    sast_sven = [v['sven'] for v in sast_norm.values()]
    sast_seceval = [v['seceval'] for v in sast_norm.values()]
    
    # Combined data
    all_sven = llm_sven + sast_sven
    all_seceval = llm_seceval + sast_seceval

    # Calculate Spearman correlations
    spearman_all, p_all = stats.spearmanr(all_sven, all_seceval)
    spearman_llm, p_llm = stats.spearmanr(llm_sven, llm_seceval)
    
    # SAST: with only 2 points, p-value is not meaningful
    spearman_sast, p_sast = stats.spearmanr(sast_sven, sast_seceval)
    if len(sast_sven) < 3:
        p_sast = np.nan

    return {
        'combined': {'rho': spearman_all, 'p': p_all, 'n': len(all_sven)},
        'llm': {'rho': spearman_llm, 'p': p_llm, 'n': len(llm_sven)},
        'sast': {'rho': spearman_sast, 'p': p_sast, 'n': len(sast_sven)},
        'normalised_scores': {
            'llm': llm_norm,
            'sast': sast_norm
        }
    }


if __name__ == "__main__":
    # Data from the ALPHA results table
    llm_data = {
        'Qwen2.5-Coder-32B': {'sven': 574.7, 'seceval': 617.8},
        'Mistral-7B': {'sven': 923.3, 'seceval': 1156.9},
        'Qwen2.5-Coder-7B': {'sven': 753.2, 'seceval': 921.5},
        'Llama3.1-8B': {'sven': 813.5, 'seceval': 856.5},
        'Phi4-14B': {'sven': 646.4, 'seceval': 797.4},
        'DeepSeek-Coder-6.7B': {'sven': 2557.0, 'seceval': 1228.5},
        'Devstral-24B': {'sven': 695.1, 'seceval': 578.5},
    }

    sast_data = {
        'CodeQL': {'sven': 5981.9, 'seceval': 1261.0},
        'Semgrep': {'sven': 3663.5, 'seceval': 1307.6},
    }

    # Compute statistics
    results = compute_alpha_correlations(
        llm_data=llm_data,
        sast_data=sast_data,
        normalise=True
    )

    print("=" * 60)
    print("ALPHA Correlation Analysis")
    print("=" * 60)
    print()
    print("Spearman Correlation Results:")
    print("-" * 40)
    print(f"  Combined (n={results['combined']['n']}):  "
          f"rho = {results['combined']['rho']:.3f}, "
          f"p = {results['combined']['p']:.4f}")
    print(f"  LLMs only (n={results['llm']['n']}):     "
          f"rho = {results['llm']['rho']:.3f}, "
          f"p = {results['llm']['p']:.4f}")
    print(f"  SAST only (n={results['sast']['n']}):     "
          f"rho = {results['sast']['rho']:.3f}, "
          f"p = {results['sast']['p']}")
    print()
    
    # Print normalised scores for reference
    print("Normalised ALPHA Scores (per sample):")
    print("-" * 40)
    print("LLMs:")
    for name, scores in sorted(results['normalised_scores']['llm'].items(), 
                                key=lambda x: x[1]['sven']):
        print(f"  {name:25s}  SVEN: {scores['sven']:.2f}  SecEval: {scores['seceval']:.2f}")
    print()
    print("SAST Tools:")
    for name, scores in sorted(results['normalised_scores']['sast'].items(), 
                                key=lambda x: x[1]['sven']):
        print(f"  {name:25s}  SVEN: {scores['sven']:.2f}  SecEval: {scores['seceval']:.2f}")
    print()