import json
import numpy as np
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score

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
        dict: {'lambda', 'a', 'r2', 'success'}
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
        popt, _ = curve_fit(
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
            'success': True
        }
        
    except:
        return {'lambda': np.nan, 'a': np.nan, 'r2': np.nan, 'success': False}


def analyze_individual_datasets(data_path):
    """Analyze each model-dataset combination individually."""
    data = load_influence_data(data_path)
    results = []
    
    print("Individual Dataset Analysis:")
    print("=" * 50)
    
    for model_data in data:
        model = model_data['model']
        
        for dataset_data in model_data['effectiveness']:
            dataset = dataset_data['dataset']
            effectiveness = dataset_data['effectiveness']
            
            x_data = list(range(len(effectiveness)))
            fit_result = fit_single_dataset(x_data, effectiveness)
            
            result = {
                'model': model,
                'dataset': dataset,
                'lambda': fit_result['lambda'],
                'a': fit_result['a'],
                'r2': fit_result['r2'],
                'success': fit_result['success']
            }
            results.append(result)
            
            if fit_result['success']:
                print(f"{model}/{dataset}: λ={fit_result['lambda']:.4f}, R²={fit_result['r2']:.4f}")
            else:
                print(f"{model}/{dataset}: FAILED")
    
    return results


def analyze_model_combined(data_path):
    """Analyze each model with all its datasets combined."""
    data = load_influence_data(data_path)
    results = []
    
    print("\nModel Combined Analysis:")
    print("=" * 50)
    
    for model_data in data:
        model = model_data['model']
        
        # Combine all datasets for this model
        all_x = []
        all_y = []
        
        for dataset_data in model_data['effectiveness']:
            effectiveness = dataset_data['effectiveness']
            x_data = list(range(len(effectiveness)))
            
            all_x.extend(x_data)
            all_y.extend(effectiveness)
        
        fit_result = fit_single_dataset(all_x, all_y)
        
        result = {
            'model': model,
            'dataset': 'ALL_COMBINED',
            'lambda': fit_result['lambda'],
            'a': fit_result['a'],
            'r2': fit_result['r2'],
            'success': fit_result['success']
        }
        results.append(result)
        
        if fit_result['success']:
            print(f"{model}/ALL: λ={fit_result['lambda']:.4f}, R²={fit_result['r2']:.4f}")
        else:
            print(f"{model}/ALL: FAILED")
    
    return results


def main():
    """Run the complete analysis."""
    data_path = "DDI/data/norm_effect_data_wo_attempt_0.json"
    
    # Individual datasets
    individual_results = analyze_individual_datasets(data_path)
    
    # Model combined
    combined_results = analyze_model_combined(data_path)
    
    return individual_results, combined_results

if __name__ == "__main__":
    individual, combined = main()
    # print(individual)
    # print(combined)