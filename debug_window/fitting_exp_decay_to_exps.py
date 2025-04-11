import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

# Exponential decay function
def exp_decay(x, a, lambda_val):
    return a * np.exp(-lambda_val * x)

# Raw data extracted from the paper
data = {
    "GPT-4": {
        "HumanEval": {
            "means": [92.0, 3.8, 1.9, 1.1, 1.1, 0.2],
            "stdevs": [1.4, 0.7, 1.1, 0.4, 0.7, 0.4]
        },
        "HumanEval-ET": {
            "means": [88.0, 8.2, 2.3, 0.8, 0.6, 0.0],
            "stdevs": [3.7, 4.3, 1.4, 0.4, 0.0, 0.0]
        },
        "MBPP": {
            "means": [70.6, 18.0, 5.9, 3.0, 1.4, 1.2],
            "stdevs": [1.0, 1.1, 1.5, 0.3, 0.5, 0.4]
        },
        "MBPP-ET": {
            "means": [67.5, 17.2, 8.6, 3.2, 1.9, 1.6],
            "stdevs": [0.8, 1.6, 0.5, 0.3, 0.2, 0.2]
        }
    },
    "GPT-3.5": {
        "HumanEval": {
            "means": [81.9, 9.7, 4.0, 1.2, 2.1, 1.0],
            "stdevs": [0.6, 0.3, 0.4, 0.8, 0.0, 0.4]
        },
        "HumanEval-ET": {
            "means": [77.2, 13.2, 5.3, 1.9, 1.4, 1.0],
            "stdevs": [1.5, 0.4, 3.0, 1.1, 0.7, 1.1]
        },
        "MBPP": {
            "means": [74.6, 15.1, 5.2, 2.6, 1.3, 1.3],
            "stdevs": [1.8, 0.9, 0.7, 0.5, 0.4, 0.8]
        },
        "MBPP-ET": {
            "means": [70.3, 16.2, 6.6, 3.3, 2.0, 1.5],
            "stdevs": [1.3, 0.2, 1.5, 0.1, 0.1, 0.2]
        }
    },
    "Qwen": {
        "HumanEval": {
            "means": [79.3, 14.9, 2.6, 1.5, 0.6, 1.1],
            "stdevs": [1.4, 2.5, 0.7, 0.4, 0.6, 1.0]
        },
        "HumanEval-ET": {
            "means": [81.3, 13.1, 2.2, 1.7, 1.5, 0.2],
            "stdevs": [0.4, 2.0, 0.8, 1.0, 0.7, 0.4]
        },
        "MBPP": {
            "means": [60.9, 22.4, 7.5, 4.5, 2.9, 1.8],
            "stdevs": [0.7, 0.4, 0.2, 0.5, 0.3, 0.3]
        },
        "MBPP-ET": {
            "means": [59.7, 21.6, 8.7, 5.0, 2.9, 2.2],
            "stdevs": [1.2, 0.7, 0.4, 0.3, 0.3, 0.5]
        },
        "BigCodeBench": {
            "means": [67.2, 14.9, 7.1, 4.7, 3.4, 2.7],
            "stdevs": [0.9, 0.9, 0.5, 0.8, 0.7, 0.2]
        }
    }
}

# Define models and datasets
models = ["GPT-4", "GPT-3.5", "Qwen"]
datasets = {
    "GPT-4": ["HumanEval", "HumanEval-ET", "MBPP", "MBPP-ET"],
    "GPT-3.5": ["HumanEval", "HumanEval-ET", "MBPP", "MBPP-ET"],
    "Qwen": ["HumanEval", "HumanEval-ET", "MBPP", "MBPP-ET", "BigCodeBench"]
}


def generate_possible_values(mean, stdev, num_experiments=3):
    """
    Generate all possible values for the original experiments given the mean and standard deviation.
    """
    if stdev == 0:
        # If standard deviation is 0, all values are equal to the mean
        return [mean] * num_experiments
    
    # For 3 experiments, use mean-delta, mean, mean+delta
    delta = stdev * np.sqrt(3/2)
    values = [mean - delta, mean, mean + delta]
    
    return values


def fit_exp_decay_to_all_data(all_data_points, x_values):
    """
    Fit exponential decay function to combined data and return parameters and R²
    """
    # Convert inputs to numpy arrays to ensure proper handling
    all_data_points = np.array(all_data_points)
    x_values = np.array(x_values)
    
    # Avoid fitting errors by ensuring no negative or zero values
    y_data = np.array([max(y, 0.001) for y in all_data_points])
    
    popt, _ = curve_fit(exp_decay, x_values, y_data, p0=[y_data[0], 1.0], maxfev=10000)
    a, lambda_val = popt
    
    # Calculate R-squared
    y_pred = exp_decay(x_values, *popt)
    ss_tot = np.sum((y_data - np.mean(y_data))**2)
    ss_res = np.sum((y_data - y_pred)**2)
    r_squared = 1 - (ss_res / ss_tot)
    
    return {
        'a': a,
        'lambda': lambda_val,
        'r_squared': r_squared
    }


print("\n\nSummary of Results:")
print("Model\tDataset\t\tR²")
print("-" * 40)

for model in models:
    model_r2_sum = 0
    model_lambda_sum = 0
    dataset_count = 0
    
    for dataset in datasets[model]:
        # Reconstruct all data points for function fitting
        # Use 1d array only
        all_values = []
        all_x_values = []
        
        for attempt in range(6):
            values = generate_possible_values(data[model][dataset]["means"][attempt], 
                                              data[model][dataset]["stdevs"][attempt])
            
            for exp_value in values:
                all_values.append(exp_value)
                all_x_values.append(attempt)
        
        # Fit and get parameters
        fit_result = fit_exp_decay_to_all_data(all_values, all_x_values)
        
        # Print results for this dataset
        temp = "\t\t" \
                if "MBPP" in dataset \
                else "\t"
                
        print(f"{model}\t{dataset}{temp}{fit_result['r_squared']:.3f}")
    print("-" * 40)


def plot_curves_only():
    """Plot only the fitted exponential decay curves."""
    plt.figure(figsize=(12, 8))
    
    model_colors = {"GPT-4": 'red', "GPT-3.5": 'blue', "Qwen": 'green'}
    dataset_line_styles = {
        "HumanEval": '-', 
        "HumanEval-ET": (0, (1, 1)),
        "MBPP": '--', 
        "MBPP-ET": '-.', 
        "BigCodeBench": (0, (3, 1, 1, 1))
    }

    
    # Smooth x range for curves
    x_smooth = np.linspace(0, 5, 100)
    
    for model in models:
        for dataset in datasets[model]:
            # Collect all data points for fitting
            all_values = []
            all_x_values = []
            
            for attempt in range(6):
                values = generate_possible_values(
                    data[model][dataset]["means"][attempt],
                    data[model][dataset]["stdevs"][attempt]
                )
                
                for exp_value in values:
                    all_values.append(exp_value)
                    all_x_values.append(attempt)
            
            # Fit the curve
            fit_result = fit_exp_decay_to_all_data(all_values, all_x_values)
            a = fit_result['a']
            lambda_val = fit_result['lambda']
            r_squared = fit_result['r_squared']
            
            # Plot the fitted curve
            y_fit = exp_decay(x_smooth, a, lambda_val)
            plt.plot(x_smooth, y_fit, linestyle='-', color=model_colors[model], 
                    #  label=f"{model} - {dataset} (λ={lambda_val:.2f}, R²={r_squared:.4f})")
                    label=f"{model} - {dataset} (R²={r_squared:.4f})")
    
    plt.xlabel('Attempt Number')
    plt.ylabel('Independent Influence (%)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize='small', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig('decay_curves_only.png', dpi=300, bbox_inches='tight')
    plt.show()


def plot_with_means():
    """Plot means with error bars and fitted curves."""
    plt.figure(figsize=(12, 8))
    
    model_colors = {"GPT-4": 'red', "GPT-3.5": 'blue', "Qwen": 'green'}
    dataset_line_styles = {
        "HumanEval": '-', 
        "HumanEval-ET": (0, (1, 1)),
        "MBPP": '--', 
        "MBPP-ET": '-.', 
        "BigCodeBench": (0, (3, 1, 1, 1))
    }

    
    # Markers for datasets
    dataset_markers = {
        "HumanEval": 'o', "HumanEval-ET": 's', 
        "MBPP": '^', "MBPP-ET": 'D', "BigCodeBench": '*'
    }
    
    # Smooth x range for curves
    x_smooth = np.linspace(0, 5, 100)
    
    for model in models:
        for dataset in datasets[model]:
            # Get means and standard deviations
            x_data = np.arange(6)
            y_means = np.array(data[model][dataset]["means"])
            y_stdevs = np.array(data[model][dataset]["stdevs"])
            
            # Collect all data points for fitting
            all_values = []
            all_x_values = []
            
            for attempt in range(6):
                values = generate_possible_values(
                    data[model][dataset]["means"][attempt],
                    data[model][dataset]["stdevs"][attempt]
                )
                
                for exp_value in values:
                    all_values.append(exp_value)
                    all_x_values.append(attempt)
            
            # Fit the curve
            fit_result = fit_exp_decay_to_all_data(all_values, all_x_values)
            a = fit_result['a']
            lambda_val = fit_result['lambda']
            r_squared = fit_result['r_squared']
            
            # Plot means with error bars
            plt.errorbar(x_data, y_means, yerr=y_stdevs, 
                         fmt=dataset_markers[dataset], color=model_colors[model], alpha=0.6)
            
            # Plot the fitted curve
            y_fit = exp_decay(x_smooth, a, lambda_val)
            plt.plot(x_smooth, y_fit, linestyle='-', color=model_colors[model], 
                    #  label=f"{model} - {dataset} (λ={lambda_val:.2f}, R²={r_squared:.4f})")
                    label=f"{model} - {dataset} (R²={r_squared:.4f})")
    
    plt.xlabel('Attempt Number')
    plt.ylabel('Independent Influence (%)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize='small', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig('decay_with_means.png', dpi=300, bbox_inches='tight')
    plt.show()


def plot_all_data():
    """Plot all data points and fitted curves."""
    plt.figure(figsize=(12, 8))
    
    # Colors for each model
    model_colors = {"GPT-4": 'red', "GPT-3.5": 'blue', "Qwen": 'green'}
    
    # Markers for datasets
    dataset_markers = {
        "HumanEval": 'o', "HumanEval-ET": 's', 
        "MBPP": '^', "MBPP-ET": 'D', "BigCodeBench": '*'
    }
    
    # Smooth x range for curves
    x_smooth = np.linspace(0, 5, 100)
    
    for model in models:
        for dataset in datasets[model]:
            # Collect all data points for fitting
            all_values = []
            all_x_values = []
            
            for attempt in range(6):
                values = generate_possible_values(
                    data[model][dataset]["means"][attempt],
                    data[model][dataset]["stdevs"][attempt]
                )
                
                for exp_value in values:
                    all_values.append(exp_value)
                    all_x_values.append(attempt)
            
            # Fit the curve
            fit_result = fit_exp_decay_to_all_data(all_values, all_x_values)
            a = fit_result['a']
            lambda_val = fit_result['lambda']
            r_squared = fit_result['r_squared']
            
            # Plot all data points
            plt.scatter(all_x_values, all_values, marker=dataset_markers[dataset], 
                        color=model_colors[model], alpha=0.3)
            
            # Plot the fitted curve
            y_fit = exp_decay(x_smooth, a, lambda_val)
            plt.plot(x_smooth, y_fit, '-', color=model_colors[model], 
                    #  label=f"{model} - {dataset} (λ={lambda_val:.2f}, R²={r_squared:.4f})")
                    label=f"{model} - {dataset} (R²={r_squared:.4f})")
    
    plt.xlabel('Attempt Number')
    plt.ylabel('Independent Influence (%)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize='small', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig('decay_with_all_data.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    
def plot_with_means_improved():
    """Plot means with clear error bars and fitted curves with complete legend."""
    plt.figure(figsize=(12, 8))
    
    # Define colors, markers, and line styles
    model_colors = {"GPT-4": 'red', "GPT-3.5": 'blue', "Qwen": 'green'}
    model_line_styles = {
        "GPT-4": '-',
        "GPT-3.5": '--',
        "Qwen": (0, (1, 1))
    }
    dataset_markers = {
        "HumanEval": 'o', 
        "HumanEval-ET": 's', 
        "MBPP": '^', 
        "MBPP-ET": 'D', 
        "BigCodeBench": '*'
    }
    
    # Smooth x range for curves
    x_smooth = np.linspace(0, 5, 100)
    
    # Create list to store legend handles and labels
    legend_handles = []
    legend_labels = []
    
    for model in models:
        for dataset in datasets[model]:
            # Get means and standard deviations
            x_data = np.arange(6)
            y_means = np.array(data[model][dataset]["means"])
            y_stdevs = np.array(data[model][dataset]["stdevs"])
            
            # Collect all data points for fitting
            all_values = []
            all_x_values = []
            
            for attempt in range(6):
                values = generate_possible_values(
                    data[model][dataset]["means"][attempt],
                    data[model][dataset]["stdevs"][attempt]
                )
                
                for exp_value in values:
                    all_values.append(exp_value)
                    all_x_values.append(attempt)
            
            # Fit the curve
            fit_result = fit_exp_decay_to_all_data(all_values, all_x_values)
            a = fit_result['a']
            lambda_val = fit_result['lambda']
            r_squared = fit_result['r_squared']
            
            # Label for this model-dataset combination
            label = f"{model} - {dataset}"
            
            # Plot means with error bars
            errorbar = plt.errorbar(
                x_data, 
                y_means, 
                yerr=y_stdevs, 
                fmt=dataset_markers[dataset], 
                color=model_colors[model], 
                markersize=8,  # Larger markers
                capsize=5,     # Add caps to error bars
                capthick=1.5,  # Thicker caps
                elinewidth=1.5, # Thicker error bars
                label=None  # We'll create a custom legend
            )
            
            # Plot the fitted curve
            y_fit = exp_decay(x_smooth, a, lambda_val)
            line = plt.plot(
                x_smooth, 
                y_fit, 
                linestyle=model_line_styles[model], 
                color=model_colors[model], 
                linewidth=2.5,  # Slightly thicker lines
                label=None  # We'll create a custom legend
            )[0]
            
            # Create custom legend entry that shows both line and marker
            from matplotlib.lines import Line2D
            legend_entry = Line2D(
                [0], [0],
                marker=dataset_markers[dataset],
                color=model_colors[model],
                linestyle=model_line_styles[model],
                markersize=8,
                linewidth=2.5,
                label=f"{label} (R²={r_squared:.3f})"
            )
            
            # Add to legend lists
            legend_handles.append(legend_entry)
            legend_labels.append(f"{label} (R²={r_squared:.3f})")
    
    # Customize plot
    plt.xlabel('Attempt Number', fontsize=18)
    plt.ylabel('Independent Influence (%)', fontsize=18)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(np.arange(6), fontsize=16)  # Show integer ticks for attempt numbers
    plt.yticks(fontsize=16)
    plt.tick_params(axis='both', which='major', labelsize=16)
    
    # Add custom legend with all 13 entries
    plt.legend(
        handles=legend_handles,
        fontsize=14,
        bbox_to_anchor=(0.58, 1), 
        loc='upper left',
        frameon=False,
        # framealpha=1,
        facecolor='white'
    )
    
    plt.tight_layout()
    plt.savefig('decay_with_means_all_entries.png', dpi=300, bbox_inches='tight')
    plt.show()


plot_with_means_improved()
# plot_curves_only()    # Only fitted curves
# plot_with_means()     # Mean values with error bars and fitted curves
# plot_all_data()       # All reconstructed data points and fitted curves