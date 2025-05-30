# =============================================================================================
# Usage:
# - get_norm_debugging_influence
# - fit_exponential_decay
# - calculate_optimal_attempts
# - get_DDI
# - plot_decay_curve
# =============================================================================================

import sys, os
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import numpy as np
import pandas as pd
import json
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from typing import Dict, Tuple, Optional

from services.Base import ServiceBase
from utils.output_message_format.output_colour import print_error, print_success, print_warning

class DDI(ServiceBase):
    def __init__(self, 
                 file_path: str,
                 model_name: str,
                 maximum_debugging_attempts: int,
                 dataset: str = "N/A",
                 theta: list[int] = [50, 80, 90, 95, 99],
                 output_dir: str = "ddi_results") -> None:
        """
        Debugging Decay Index (DDI) implementation.

        Args:
            file_path (str): Path to the file containing debugging effectiveness data.
                Effectiveness data is not normalised.
            model_name (str): Name of the model used for debugging.
            maximum_debugging_attempts (int): Maximum number of debugging attempts to consider,
                total attempts including the initial attempt would be maximum_attempts + 1.
            dataset (str): Name of the dataset used for debugging, default is "N/A".
            theta (list[int]): List of effectiveness thresholds (0-100) for optimal attempt calculation.
        output_dir (str): Directory to save DDI results, default is "ddi_results".
        """
        super().__init__()
        self.file_path = file_path
        self.maximum_debugging_attempts = maximum_debugging_attempts
        self.theta = theta
        self.model_name = model_name
        self.dataset = dataset
        self.output_dir = output_dir
        
        
    def _extract_data_arrays(self, 
                             effectiveness_data: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray]:
       """
       Extract and sort effectiveness data into numpy arrays.
       
       Args:
           effectiveness_data: Dict with keys like "E_0", "D_1", etc.
           
       Returns:
           Tuple of (attempts, effectiveness_values)
       """
       # Extract attempt numbers and effectiveness values
       attempts = []
       effectiveness = []
       
       for key, value in effectiveness_data.items():
           if key.startswith(("E_", "D_")):
               # Extract attempt number from key (E_0 -> 0, D_1 -> 1, etc.)
               attempt_num = int(key.split("_")[1])
               attempts.append(attempt_num)
               effectiveness.append(value)
       
       # Sort by attempt number
       sorted_indices = np.argsort(attempts)
       attempts_array = np.array(attempts)[sorted_indices]
       effectiveness_array = np.array(effectiveness)[sorted_indices]
       
       return attempts_array, effectiveness_array
   
   
    def _exponential_model(self, t: np.ndarray, E_0: float, lambda_val: float) -> np.ndarray:
       """
       Exponential decay model: E(t) = E_0 * exp(-λt)
       
       Args:
           t: Array of attempt numbers
           E_0: Initial effectiveness
           lambda_val: Decay constant
           
       Returns:
           Array of predicted effectiveness values
       """
       return E_0 * np.exp(-lambda_val * t)
   
   
    def _get_filename_prefix(self) -> str:
        """
        Get the filename prefix based on model name and dataset.
        
        Returns:
            str: Filename prefix for saving DDI results.
        """
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        ds = "" if self.dataset == "N/A" else f"_{self.dataset}"
        file_path = os.path.join(self.output_dir, f"{self.model_name}{ds}")
        
        return file_path
   
   
    def _save_DDI(self, result: dict) -> None:
        """
        Save DDI to a json file in the output directory.

        Args:
            result (dict): Dictionary containing DDI results to save.
        """            
        file_path = f"{self._get_filename_prefix()}_DDI.json"
        try:
            with open(file_path, 'w') as f:
                json.dump(result, f, indent=4)
            print_success(f"DDI results saved to: {file_path}")
        except Exception as e:
            print_error(f"Failed to save DDI results: {str(e)}")
        
        
    def get_norm_debugging_influence(self, is_DDI:bool = True) -> dict:
        """
        Calculate the normalised influence of each self-debugging attempt using formula:
        I_i = S_i / N_i
        
        Where:
            - I_i is the influence of attempt i
            - S_i is the number of problems solved at attempt i
            - N_i is the number of problems remaining before attempt i
            
        
        Args:
            file_path (str): Path to the CSV file containing results
            maximum_debugging_attempts (int): Maximum number of debugging attempts to consider,
                total attempts including the initial attempt would be maximum_attempts + 1.
            is_DDI (bool): Flag to indicate if the calculation is for DDI
            
        Returns:
            dict: Dictionary containing influence metrics for each attempt
        """    
        try:
            df = pd.read_csv(self.file_path)
        except FileNotFoundError:
            print_error(f"Could not generate DDI, file not found: {self.file_path}")
            raise FileNotFoundError(f"Could not generate DDI, file not found: {self.file_path}")
        
        # Total attempts
        attempts = self.maximum_debugging_attempts + 1
        
        # DDI
        norm_effectiveness = []
        norm_effectiveness_key = ["E_0"]
        norm_effectiveness_key.extend([f"D_{i}"for i in range(1, attempts + 1)])
        
        # Get the value counts for successful attempts (status == "pass")
        pass_counts = df[df["status"] == "pass"]["fix_mode_attempt_count"]\
                                        .value_counts()\
                                        .sort_index()
        
        # Total number of problems
        N = len(df)
        
        results = {
            "total_problems": N,
            "attempts": {},
            "summary": []
        }
        
        # Calculate S_i (number of problems solved at attempt i) for each attempt
        S = {}
        for attempt in range(attempts):
            S[attempt] = pass_counts.get(attempt, 0)
        
        # Calculate N_i and I_i for each attempt
        cumulative_solved = 0
        
        for i in range(6):  # 0 to 5 attempts
            # N_i = N - sum of all problems solved in previous attempts
            N_i = N - cumulative_solved
            
            # S_i = number of problems solved at attempt i
            S_i = S[i]
            
            # I_i = S_i / N_i (influence of attempt i)
            if N_i > 0:
                I_i = S_i / N_i
            else:
                I_i = 0.0
            
            results["attempts"][i] = {
                "S_i": S_i,           # Problems solved at attempt i
                "N_i": N_i,           # Problems remaining before attempt i
                "I_i": I_i,           # Normalized influence
                "I_i percent": I_i * 100  # Influence as percentage
            }
            
            # Update cumulative count
            cumulative_solved += S_i
            
            # Add to summary
            if N_i > 0:  # Only include attempts where there were problems to solve
                results["summary"].append(f"Attempt {i}: {S_i}/{N_i} = {I_i:.4f} ({I_i*100:.2f}%)")
                norm_effectiveness.append(round(I_i*100, 4))
        
        # Calculate overall success rate
        total_solved = sum(S.values())
        overall_success_rate = total_solved / N
        results["total_solved"] = total_solved
        results["overall_success_rate"] = overall_success_rate
        results["overall_success_percent"] = overall_success_rate * 100
        for n_e, n_k in zip(norm_effectiveness, norm_effectiveness_key):
            results.setdefault("DDI", {})[n_k] = n_e
        
        return results["DDI"] \
                if is_DDI \
                else results # for debugging

   
    def fit_exponential_decay(self, 
                              effectiveness_data: Dict[str, float]) -> Tuple[float, float, float]:
       """
       Fit exponential decay model to effectiveness data.
       
       Args:
           effectiveness_data: Dict containing effectiveness values
           
       Returns:
           Tuple of (lambda_estimate, E_0_estimate, r_squared)
           
       Raises:
           ValueError: If fitting fails or insufficient data points
       """
       attempts, effectiveness = self._extract_data_arrays(effectiveness_data)
       
       if len(attempts) < 2:
           raise ValueError("Insufficient data points for exponential fitting (need at least 3)")
       
       # Filter out non-positive values for stability
       valid_mask = effectiveness > 0
       if np.sum(valid_mask) < 2:
           raise ValueError("Insufficient positive effectiveness values for fitting")
       
       valid_attempts = attempts[valid_mask]
       valid_effectiveness = effectiveness[valid_mask]
       
       try:
           # Initial parameter estimates
           initial_E_0 = valid_effectiveness[0]
           initial_lambda = 0.5
           
           # Fit the exponential model
           popt, pcov = curve_fit(
               self._exponential_model,
               valid_attempts,
               valid_effectiveness,
               p0=[initial_E_0, initial_lambda],
               bounds=([0, 0], [np.inf, np.inf]),  # Ensure positive parameters
               maxfev=10000
           )
           
           E_0_estimate, lambda_estimate = popt
           
           # Calculate R-squared using all original data points
           y_predicted = self._exponential_model(attempts, E_0_estimate, lambda_estimate)
           ss_residual = np.sum((effectiveness - y_predicted) ** 2)
           ss_total = np.sum((effectiveness - np.mean(effectiveness)) ** 2)
           r_squared = 1 - (ss_residual / ss_total) if ss_total > 0 else 0
           
           return lambda_estimate, E_0_estimate, r_squared
           
       except Exception as e:
           raise ValueError(f"Exponential fitting failed: {str(e)}")
   
   
    def calculate_optimal_attempts(self, 
                                   lambda_val: float, 
                                   theta: float) -> float:
       """
       Calculate optimal number of attempts using DDI formula.
       
       Args:
           lambda_val: Decay constant from exponential fit
           theta: Effectiveness threshold percentage (0-100)
           
       Returns:
           Optimal number of attempts (t_θ)
           
       Raises:
           ValueError: If lambda is non-positive or theta is invalid
       """
       if lambda_val <= 0:
           raise ValueError("Lambda must be positive for optimal attempts calculation")
       
       if not (0 < theta < 100):
           raise ValueError("Theta must be between 0 and 100 (exclusive)")
       
       # DDI formula: t_θ = ln(100/(100-θ)) / λ
       optimal_attempts = np.log(100 / (100 - theta)) / lambda_val
       
       return optimal_attempts
   
   
    def get_DDI(self) -> dict:
        """
        Get DDI analysis results including fitting and optimal attempts.
        """
        norm_effectiveness = self.get_norm_debugging_influence(is_DDI=False)
        fitted_lambda, fitted_e_0, r_2 =  self.fit_exponential_decay(norm_effectiveness["DDI"])
        t_theta = []
        for theta in self.theta:
            t_theta.append(self.calculate_optimal_attempts(fitted_lambda, theta))
        
        return {
            "E_0": norm_effectiveness["DDI"].get("E_0", None),
            "lambda": fitted_lambda,
            "fitted_E_0": fitted_e_0,
            "r_squared": r_2,
            "theta": self.theta,
            "t_theta": t_theta,
            "t_theta_ceiling": [int(np.ceil(t)) for t in t_theta],
            "fit_quality": "excellent" if r_2 > 0.9 else "good" if r_2 > 0.7 else "poor",
            "A_phi": round(norm_effectiveness["overall_success_percent"], 4),
            "normalised_effectiveness": norm_effectiveness["DDI"]
        }
        

    def plot_decay_curve(self, save_path: str = None, show_plot: bool = True):
        """
        Plot the exponential decay curve with optimal attempt markers.
        
        Args:
            save_path (str, optional): Path to save the plot
            show_plot (bool): Whether to display the plot
        """
        try:
            # Get DDI results
            ddi_results = self.get_DDI()
            norm_effectiveness = self.get_norm_debugging_influence(is_DDI=False)
            
            # Extract data for plotting
            attempts_data, effectiveness_data = self._extract_data_arrays(norm_effectiveness["DDI"])
            fitted_lambda = ddi_results["lambda"]
            fitted_E_0 = ddi_results["fitted_E_0"]
            r_squared = ddi_results["r_squared"]
            optimal_attempts = ddi_results["t_theta_ceiling"]
            theta_values = ddi_results["theta"]
            
            # Create the plot
            plt.figure(figsize=(10, 6))
            
            # # Plot actual data points
            # plt.scatter(attempts_data, effectiveness_data, color='blue', s=60, 
            #         alpha=0.7, label='Actual Data', zorder=5)
            
            # Plot fitted exponential curve
            x_smooth = np.linspace(0, max(optimal_attempts), 100)
            y_smooth = self._exponential_model(x_smooth, fitted_E_0, fitted_lambda)
            plt.plot(x_smooth, y_smooth, 'r-', linewidth=2, 
                    label=f'Fitted: E(t) = {fitted_E_0:.2f} × exp(-{fitted_lambda:.3f}t)')
            
            for i, (theta, t_optimal) in enumerate(zip(theta_values, optimal_attempts)):
                
                # Vertical line at optimal attempt
                plt.axvline(x=t_optimal, color="grey", linestyle='--', alpha=0.5, linewidth=1.5)
                
                # Calculate effectiveness at optimal attempt
                y_at_optimal = self._exponential_model(t_optimal, fitted_E_0, fitted_lambda)
                
                # Horizontal line at effectiveness level
                plt.axhline(y=y_at_optimal, color="grey", linestyle='--', alpha=0.5, linewidth=1.5)
                
                # text annotation
                text_x = t_optimal + 0.1
                text_y = y_at_optimal + 1
                
                # edge case for high theta values
                if text_y > max(effectiveness_data) * 0.9:
                    text_y = y_at_optimal - 3
                if text_x > max(optimal_attempts) - 0.5:
                    text_x = t_optimal - 0.25
                
                plt.text(text_x, text_y, f'θ={theta}%', 
                        fontsize=9, color="black", ha='left', va='bottom')
            
            # Customize plot
            plt.xlabel('Attempt', fontsize=12)
            plt.ylabel('Effectiveness (%)', fontsize=12)
            plt.title(f'Model: {self.model_name}, Dataset: {self.dataset}\n'
                      f'DDI(θ = {self.theta}, φ = 1)\n'
                      f'E\u2080 = {ddi_results["E_0"]:.1f}%, '
                      f'λ = {fitted_lambda:.4f}, '
                      f'A\u1D60 = {ddi_results["A_phi"]}, '
                      f'R² = {r_squared:.4f}', fontsize=14)
            
            plt.legend(loc='upper right')
            
            # axis limits
            plt.xlim(0, max(optimal_attempts) + 0.25)
            plt.ylim(0, max(effectiveness_data) * 1.1)
            
            plt.tight_layout()
            
            # Save plot if path provided
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print_success(f"Plot saved to: {save_path}")
            
            # Show plot if requested
            if show_plot:
                plt.show()
            else:
                plt.close()
                
        except Exception as e:
            print_error(f"Failed to create plot: {str(e)}")
            raise
        
    
    def __call__(self):
        """
        Call method to execute DDI analysis.
        """
        try:
            ddi_results = self.get_DDI()
            self._save_DDI(ddi_results)
            self.plot_decay_curve(save_path=f"{self._get_filename_prefix()}_DDI_decay_curve.png", 
                                  show_plot=False)
        except Exception as e:
            print_error(f"Error during DDI analysis: {str(e)}")
            raise e        
    
    
    def cleanup(self):
        """
        Cleanup resources if needed.
        """
        print_success("DDI cleanup completed.")
        # No specific cleanup needed for this service, but can be overridden if necessary.
        

if __name__ == "__main__":
    ddi = DDI(model_name="phi4", dataset="Humaneval",
              file_path="experiment_results/phi4_HumanEval_results.csv",
              maximum_debugging_attempts=5,
              theta=[50, 80, 90, 95, 99])
    ddi()