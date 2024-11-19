import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import argparse
from typing import Optional, List

# Utils
from utils.output_message_format.output_colour import print_model_output, print_info, print_error, print_success, print_warning

# Data
from data.DatasetBase import DatasetBase
from data.MBPP.MBPP import MBPP
from data.HumanEval.HumanEval import HumanEval
from data.DS1000.DS1000 import DS1000

def safe_save_data(dataloader: DatasetBase, experiment_name: str, model_name: str) -> None:
    """
    Safely save data to CSV with error handling.
    Args:
        dataloader (DatasetBase): The dataloader object.
        experiment_name (str): The name of the experiment, will pass the pycapsule class name.
        model_name (str): Name of the model, used to save the data in Dataloader.
    """
    print_info(f"Saving data for {experiment_name}...")
    try:
        dataloader.log_to_csv(model_name)
    except Exception as e:
        print_error(f"Error saving data for {experiment_name}: {str(e)}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PyCapsule experiments")
    parser.add_argument("--subset-size", 
                        type = int, 
                        default = None,
                        # default = 5,
                        help="Number of samples to run from each dataset. If not specified, runs full datasets.")
    
    parser.add_argument("--datasets", 
                        nargs="+", # multiple arguments 
                        choices=["ds1000", "humaneval", "mbpp"], 
                        # default=["ds1000", "humaneval", "mbpp"],
                        default = ["mbpp"], # TODO: Change default.
                        help="Specify which datasets to run. Options: ds1000, humaneval, mbpp")
    return parser.parse_args()


def get_selected_dataloaders(args: argparse.Namespace) -> List[DatasetBase]:
    dataset_map: dict[str, DatasetBase] = {
        "ds1000": DS1000(subset_size = args.subset_size),
        "humaneval": HumanEval(subset_size = args.subset_size),
        "mbpp": MBPP(subset_size = args.subset_size)
    }
    return [dataset_map[dataset] for dataset in args.datasets]


def append_result_to_dataloader(target_dataloader: DatasetBase, data_point: dict, fix_mode_attempt_count: int, status: str) -> None:
    if target_dataloader.__class__.__name__ == "DS1000":
        target_dataloader.results.append({
            "problem_id": data_point['metadata']['problem_id'],
            "library": data_point['metadata']['library'],
            "fix_mode_attempt_count": fix_mode_attempt_count,
            "status": status
        })
    else:
        target_dataloader.results.append({
            "task_id": data_point["task_id"],
            "fix_mode_attempt_count": fix_mode_attempt_count,
            "status": status
        }) 


