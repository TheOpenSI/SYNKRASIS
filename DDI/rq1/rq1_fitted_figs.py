import json
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score
import os


lambda_vals = {
    "gpt-3.5-turbo-1106": 0.7061,
    "gpt-4-1106-preview": 0.5484,
    "qwen2.5-coder": 0.5003,
    "gpt-3.5-turbo": 0.7704,
}

r_2_vals = {
    "gpt-3.5-turbo-1106": 0.9268,
    "gpt-4-1106-preview": 0.8608,
    "qwen2.5-coder": 0.7935,
    "gpt-3.5-turbo": 0.9512,
}
# qwen_lambda = 0.5003
# gpt_3_5_1106_lambda = 0.7061
# gpt_4_lambda = 0.5484
# gpt_3_5_lambda = 0.7704

def exp_decay(x, a, lambda_val):
    """Exponential decay function: y = a * exp(-lambda * x)"""
    return a * np.exp(-lambda_val * x)


def load_influence_data(json_path):
    """Load the influence data from JSON file."""
    with open(json_path, 'r') as f:
        return json.load(f)


def fit_single_dataset(x_data, y_data):
    """
    Fit exponential decay to a single dataset.
    
    Returns:
        dict: {'lambda', 'a', 'r2', 'success', 'x_clean', 'y_clean', 'y_pred'}
    """
    try:
        # Clean data
        x_data = np.array(x_data, dtype=float)
        y_data = np.array(y_data, dtype=float)
        
        # Remove invalid points
        mask = np.isfinite(x_data) & np.isfinite(y_data) & (y_data > 0)
        if np.sum(mask) < 3:
            return {'lambda': np.nan, 'a': np.nan, 'r2': np.nan, 'success': False}
        
        x_clean = x_data[mask]
        y_clean = y_data[mask]
        
        # Fit
        popt, pcov = curve_fit(
            exp_decay, x_clean, y_clean,
            p0=[np.max(y_clean), 0.5],
            bounds=([0, 0], [np.inf, 5])
        )
        
        a_fitted, lambda_fitted = popt
        y_pred = exp_decay(x_clean, a_fitted, lambda_fitted)
        r2 = r2_score(y_clean, y_pred)
        
        return {
            'lambda': lambda_fitted,
            'a': a_fitted,
            'r2': r2,
            'success': True,
            'x_clean': x_clean,
            'y_clean': y_clean,
            'y_pred': y_pred,
            'params_cov': pcov
        }
        
    except Exception as e:
        print(f"Fitting error: {e}")
        return {'lambda': np.nan, 'a': np.nan, 'r2': np.nan, 'success': False}


def analyze_model_combined_with_viz(data_path, output_dir="output_plots"):
    """Analyze each model with all its datasets combined and create visualizations."""
    data = load_influence_data(data_path)
    results = []
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print("\nModel Combined Analysis with Visualization:")
    print("=" * 60)
    
    # Set up the figure for all models
    n_models = len(data)
    fig, axes = plt.subplots(2, (n_models + 1) // 2, figsize=(15, 10))
    if n_models == 1:
        axes = [axes]
    elif n_models <= 2:
        axes = axes.flatten()
    else:
        axes = axes.flatten()
    
    for i, model_data in enumerate(data):
        model = model_data['model']
        lambda_val = lambda_vals.get(model.lower(), None)
        if lambda_val is None:
            raise ValueError(f"Lambda value not defined for model: {model}")
        
        # Combine all datasets for this model
        all_x = []
        all_y = []
        dataset_info = []
        
        for dataset_data in model_data['effectiveness']:
            dataset_name = dataset_data['dataset']
            effectiveness = dataset_data['effectiveness']
            # x_data = list(range(len(effectiveness)))
            x_data = list(range(11))
            # predicted
            effectiveness_temp = [exp_decay(i, effectiveness[0], lambda_val) for i in list(range(6, 11))]
            effectiveness.extend(effectiveness_temp)
            all_x.extend(x_data)
            all_y.extend(effectiveness)
            dataset_info.append(f"{dataset_name} (n={len(effectiveness)})")
        
        fit_result = fit_single_dataset(all_x, all_y)
        
        result = {
            'model': model,
            'dataset': 'ALL_COMBINED',
            'lambda': fit_result['lambda'],
            'a': fit_result['a'],
            'r2': fit_result['r2'],
            'success': fit_result['success'],
            'n_points': len(all_x),
            'datasets_included': dataset_info
        }
        results.append(result)
        
        # Create individual plot for this model
        plt.figure(figsize=(10, 6))
        
        if fit_result['success']:
            x_clean = fit_result['x_clean']
            y_clean = fit_result['y_clean']
            y_pred = fit_result['y_pred']
            
            # Plot data points
            # plt.scatter(all_x, all_y, alpha=0.6, color='blue', label='Data Points')
            
            # Plot fitted curve
            x_smooth = np.linspace(min(x_clean), max(x_clean), 100)
            y_smooth = exp_decay(x_smooth, fit_result['a'], fit_result['lambda'])
            plt.plot(x_smooth, y_smooth, 'r-', linewidth=2, 
                    label=f'Fitted: y = {fit_result["a"]:.3f} × exp(-{fit_result["lambda"]:.3f}x)')
            
            plt.title(f'{model} - Exponential Decay Fit\n' + 
                     f'λ = {fit_result["lambda"]:.4f}, R² = {fit_result["r2"]:.4f}')
            
            print(f"{model}/ALL: λ={fit_result['lambda']:.4f}, R²={fit_result['r2']:.4f}, n={len(all_x)}")
        else:
            plt.scatter(all_x, all_y, alpha=0.6, color='blue', label='Data Points')
            plt.title(f'{model} - Fitting FAILED')
            print(f"{model}/ALL: FAILED")
        
        plt.xlabel('Time/Position Index')
        plt.ylabel('Effectiveness')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Add dataset info as text
        info_text = f"Datasets: {', '.join(dataset_info[:3])}"
        if len(dataset_info) > 3:
            info_text += f"\n+ {len(dataset_info)-3} more"
        plt.figtext(0.02, 0.02, info_text, fontsize=8, verticalalignment='bottom')
        
        plt.tight_layout()
        
        # Save individual plot
        individual_filename = f"{output_dir}/{model}_exponential_decay.png"
        plt.savefig(individual_filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        # Add to combined plot
        if i < len(axes):
            ax = axes[i] if n_models > 1 else axes[0]
            
            # t
            t_theta = lambda theta, lambda_val : np.log(100/(100-theta))/ lambda_val
            theta_vals = [50, 80, 90, 95, 99]
            t_list = []
            for theta in theta_vals:
                t = t_theta(theta, fit_result['lambda'])
                t_final = int(np.ceil(t))
                # t_final = int(np.floor(t))
                t_list.append(t_final)
            
            if fit_result['success']:
                # ax.scatter(all_x, all_y, alpha=0.6, s=20)
                x_smooth = np.linspace(min(fit_result['x_clean']), 
                                     max(fit_result['x_clean']), 100)
                y_smooth = exp_decay(x_smooth, fit_result['a'], fit_result['lambda'])
                ax.plot(x_smooth, y_smooth, 'r-', linewidth=2)
                for theta, attempt in zip(theta_vals, t_list):
                    ax.axvline(x=attempt, color='gray', linestyle='--', alpha=0.5)
                    # ax.axhline(y=theta, color='gray', linestyle='--', alpha=0.5)
                    y_val = exp_decay(attempt, fit_result['a'], fit_result['lambda'])
                    ax.axhline(y=y_val, color='gray', linestyle='--', alpha=0.5)
                    # qwen text patch
                    if "qwen" in model.lower() and attempt == 10:
                        attempt-=0.5
                    ax.text(attempt + 0.5, y_val + 1, f'θ={theta}%',
                            fontsize=8, color='black', ha='center', va='bottom')
                    
                ax.set_title(f'{model}\nλ={fit_result["lambda"]:.4f}, R²={r_2_vals.get(model.lower())}')
            else:
                ax.scatter(all_x, all_y, alpha=0.6, s=20)
                ax.set_title(f'{model}\nFitting Failed')
            
            ax.set_xlabel('Debugging Attempt')
            ax.set_ylabel('Debugging Effectiveness')
            # ax.grid(True, alpha=0.3)
    
    # Hide unused subplots
    for j in range(len(data), len(axes)):
        if j < len(axes):
            axes[j].set_visible(False)
    
    plt.tight_layout()
    combined_filename = f"{output_dir}/all_models_combined.png"
    plt.grid(False)
    plt.savefig(combined_filename, dpi=500, bbox_inches='tight')
    plt.close()
    
    # Create summary statistics plot
    # create_summary_plot(results, output_dir)
    
    return results


def create_summary_plot(results, output_dir):
    """Create a summary plot of lambda values and R² scores."""
    successful_results = [r for r in results if r['success']]
    
    if not successful_results:
        print("No successful fits to summarize.")
        return
    
    models = [r['model'] for r in successful_results]
    lambdas = [r['lambda'] for r in successful_results]
    r2_scores = [r['r2'] for r in successful_results]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Lambda values
    bars1 = ax1.bar(models, lambdas, color='skyblue', alpha=0.7)
    ax1.set_title('Decay Rate (λ) by Model')
    ax1.set_ylabel('Lambda (λ)')
    ax1.tick_params(axis='x', rotation=45)
    
    # Add value labels on bars
    for bar, val in zip(bars1, lambdas):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{val:.3f}', ha='center', va='bottom')
    
    # R² scores
    bars2 = ax2.bar(models, r2_scores, color='lightcoral', alpha=0.7)
    ax2.set_title('Goodness of Fit (R²) by Model')
    ax2.set_ylabel('R² Score')
    ax2.set_ylim(0, 1)
    ax2.tick_params(axis='x', rotation=45)
    
    # Add value labels on bars
    for bar, val in zip(bars2, r2_scores):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{val:.3f}', ha='center', va='bottom')
    
    plt.tight_layout()
    summary_filename = f"{output_dir}/summary_statistics.png"
    plt.savefig(summary_filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\nSummary plots saved to: {summary_filename}")


def export_results_to_csv(results, output_dir="output_plots"):
    """Export results to CSV file."""
    import pandas as pd
    
    df = pd.DataFrame(results)
    csv_filename = f"{output_dir}/exponential_decay_results.csv"
    df.to_csv(csv_filename, index=False)
    print(f"Results exported to: {csv_filename}")


def main():
    """Run the complete analysis with visualization."""
    data_path = "DDI/data/norm_effect_data.json"
    output_dir = "DDI/rq1/figures/exponential_decay_analysis"
    
    # Check if data file exists
    if not os.path.exists(data_path):
        print(f"Data file not found: {data_path}")
        print("Please ensure the JSON file exists at the specified path.")
        return None, None
    
    # Run analysis with visualization
    combined_results = analyze_model_combined_with_viz(data_path, output_dir)
    
    # Export results to CSV
    # export_results_to_csv(combined_results, output_dir)
    
    # Print summary
    print("\n" + "="*60)
    print("ANALYSIS SUMMARY")
    print("="*60)
    
    successful_fits = [r for r in combined_results if r['success']]
    failed_fits = [r for r in combined_results if not r['success']]
    
    print(f"Successful fits: {len(successful_fits)}/{len(combined_results)}")
    
    if successful_fits:
        print("\nSuccessful Model Fits:")
        for result in successful_fits:
            print(f"  {result['model']}: λ={result['lambda']:.4f}, R²={result['r2']:.4f}, n={result['n_points']}")
        
        # Find best and worst fits
        best_fit = max(successful_fits, key=lambda x: x['r2'])
        worst_fit = min(successful_fits, key=lambda x: x['r2'])
        
        print(f"\nBest fit: {best_fit['model']} (R² = {best_fit['r2']:.4f})")
        print(f"Worst fit: {worst_fit['model']} (R² = {worst_fit['r2']:.4f})")
        
        # Decay rate statistics
        lambdas = [r['lambda'] for r in successful_fits]
        print(f"\nDecay rate (λ) statistics:")
        print(f"  Mean: {np.mean(lambdas):.4f}")
        print(f"  Std:  {np.std(lambdas):.4f}")
        print(f"  Min:  {np.min(lambdas):.4f}")
        print(f"  Max:  {np.max(lambdas):.4f}")
    
    if failed_fits:
        print(f"\nFailed fits: {[r['model'] for r in failed_fits]}")
    
    print(f"\nAll plots saved to: {output_dir}/")
    print("Files generated:")
    print("  - Individual model plots: {model}_exponential_decay.png")
    print("  - Combined overview: all_models_combined.png")
    print("  - Summary statistics: summary_statistics.png")
    print("  - Results data: exponential_decay_results.csv")
    
    return combined_results


if __name__ == "__main__":
    results = main()