import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import csv
import io

# decay function y = a * exp(-lambda * t)
def exp_decay(t, a, lambda_val):
    return a * np.exp(-lambda_val * t)

# Sample data to create a CSV file for demonstration
df = pd.read_csv("sim_experiment_results.csv")

# Calculate the mean value for each attempt column
mean_values = df.mean()

# Create x-values (attempt numbers 1 through 10)
x_data = np.array(range(0, len(mean_values)))
y_data = mean_values.values

# Print the mean values for each attempt
print("Mean values for each attempt:")
for i, val in enumerate(y_data):
    print(f"Attempt {i+1}: {val:.4f}")

# Fit the exponential decay function to the data
try:
    # Initial parameter guesses: a (initial amplitude), lambda (decay constant)
    initial_guess = [y_data[0], 0.5]
    
    # Perform the curve fitting
    params, covariance = curve_fit(exp_decay, x_data, y_data, p0=initial_guess)
    
    # Extract the optimized parameters
    a_opt, lambda_opt = params
    
    # Calculate standard errors of the parameters
    perr = np.sqrt(np.diag(covariance))
    a_err, lambda_err = perr
    
    # Calculate half-life and its error
    half_life = np.log(2) / lambda_opt
    half_life_err = half_life * (lambda_err / lambda_opt)
    
    # Calculate R-squared value to assess goodness of fit
    y_fit = exp_decay(x_data, a_opt, lambda_opt)
    residuals = y_data - y_fit
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y_data - np.mean(y_data))**2)
    r_squared = 1 - (ss_res / ss_tot)
    
    # Calculate RMSE (Root Mean Square Error)
    rmse = np.sqrt(np.mean(residuals**2))
    
    # Print the results
    print("\nExponential Decay Model Results:")
    print(f"Fitted function: y = {a_opt:.4f} * exp(-{lambda_opt:.4f} * t)")
    print(f"Initial amplitude (a): {a_opt:.4f} ± {a_err:.4f}")
    print(f"Decay constant (λ): {lambda_opt:.4f} ± {lambda_err:.4f}")
    print(f"Half-life (t₁/₂): {half_life:.4f} ± {half_life_err:.4f} attempts")
    print(f"R-squared: {r_squared:.4f}")
    print(f"RMSE: {rmse:.4f}")
    
    # Calculate various decay points
    decay_percentages = [50, 75, 80, 90, 95, 99]
    print("\nTime to reach specific decay percentages:")
    for percent in decay_percentages:
        # For decay of p%, solve a*e^(-λt) = a*(1-p/100)
        # t = -ln(1-p/100)/λ
        decay_factor = percent / 100
        time_to_decay = -np.log(1 - decay_factor) / lambda_opt
        print(f"{percent}% decay: {time_to_decay:.2f} attempts")
    
    # Plot the original data points and the fitted curve
    plt.figure(figsize=(10, 6))
    plt.scatter(x_data, y_data, label='Data Points (Mean Values)', s=60, color='blue')
    
    # Generate a smoother curve for plotting
    x_smooth = np.linspace(min(x_data), max(x_data) + 2, 100)
    y_smooth = exp_decay(x_smooth, a_opt, lambda_opt)
    plt.plot(x_smooth, y_smooth, 'r-', linewidth=2, 
             label=f'Fitted: {a_opt:.2f} * exp(-{lambda_opt:.2f} * t)')
    
    # Mark the half-life point
    plt.axvline(x=half_life, color='green', linestyle='--')
    plt.axhline(y=a_opt/2, color='green', linestyle='--')
    plt.scatter([half_life], [a_opt/2], color='green', s=100, zorder=5)
    plt.text(half_life + 0.1, a_opt/2, f'Half-life = {half_life:.2f}', 
             color='green', fontweight='bold')
    
    # Add 80% decay point
    decay_80_time = -np.log(1 - 0.8) / lambda_opt
    decay_80_value = a_opt * np.exp(-lambda_opt * decay_80_time)
    plt.axvline(x=decay_80_time, color='purple', linestyle='--')
    plt.axhline(y=decay_80_value, color='purple', linestyle='--')
    plt.scatter([decay_80_time], [decay_80_value], color='purple', s=100, zorder=5)
    plt.text(decay_80_time + 0.1, decay_80_value, f'80% decay = {decay_80_time:.2f}', 
             color='purple', fontweight='bold')
    
    # Formatting
    plt.xlabel('Attempt Number')
    plt.ylabel('Value')
    plt.title('Exponential Decay Fit to Attempt Data')
    plt.legend()
    plt.grid(True)
    plt.ylim(bottom=0)  # Start y-axis at 0
    plt.savefig('exponential_fit.png')
    plt.show()
    
    # Plot residuals to check quality of fit
    plt.figure(figsize=(10, 4))
    plt.scatter(x_data, residuals, color='red')
    plt.axhline(y=0, color='black', linestyle='-')
    plt.xlabel('Attempt Number')
    plt.ylabel('Residual (Actual - Predicted)')
    plt.title('Residuals of Exponential Decay Fit')
    plt.grid(True)
    plt.savefig('residuals_exponential_fit.png')
    
except Exception as e:
    print(f"Error during curve fitting: {e}")

# To use this with an actual CSV file, replace the io.StringIO part with:
# df = pd.read_csv('your_data.csv')