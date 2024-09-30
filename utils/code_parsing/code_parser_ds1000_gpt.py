import sys, os, gc
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

import re
from typing import Optional

from utils.output_message_format.output_colour import print_error, print_warning, print_success

def parse_solution_ds1000_gpt(text: str) -> Optional[str]:
    """
    Parse the solution code from the given text.

    This function searches for a "### Solution" section in the text and extracts
    the Python code enclosed in triple backticks within that section. The "python"
    specifier after the opening backticks is optional and ignored if present.

    Args:
        text (str): The input text containing the solution.

    Returns:
        Optional[str]: The extracted solution code, or None if no solution is found.

    Raises:
        ValueError: If the input is not a string.
    """
    if not isinstance(text, str):
        raise ValueError("Input must be a string")

    # Find the Solution section
    solution_pattern = r'### Solution\s*```(?:python)?\s*(.*?)\s*```'
    solution_match = re.search(solution_pattern, text, re.DOTALL)
    
    if solution_match:
        # Extract the code within the backticks
        code = solution_match.group(1).strip()
        return code
    else:
        print_warning("No solution found in the given text")
        return None

def main():
    """
    Main function to demonstrate the usage of the parse_solution function.
    """
    sample_text = '''
To shuffle the order of the DataFrame's rows according to a given list, we can follow these steps:
1. Import necessary libraries - pandas and numpy.
2. Create a DataFrame similar to the given one.
3. Create a list of indices representing the desired order of rows.
4. Use the list of indices to reindex the DataFrame.
Here's the code to achieve this:
```python
import pandas as pd
import numpy as np
# Create the DataFrame
df = pd.DataFrame({'Col1': [1, 4, 7, 10, 13, 16],
                    'Col2': [2, 5, 8, 11, 14, 17],
                    'Col3': [3, 6, 9, 12, 15, 18],
                    'Type': [1, 1, 2, 2, 3, 3]})
# Define the desired order of rows
new_order = [2, 4, 0, 3, 1, 5]
# Reindex the DataFrame based on the new order
df = df.iloc[new_order].reset_index(drop=True)
df
```
In the above solution:
- We create a new list `new_order` which specifies the desired order of rows.
- We use `iloc` to reindex the DataFrame based on the new order list.
- Finally, we reset the index to have a continuous index starting from 0.
### Solution
```python
def shuffle_dataframe(df, new_order):
    return df.iloc[new_order].reset_index(drop=True)
result = shuffle_dataframe(df, [2, 4, 0, 3, 1, 5])
```
    '''
    solution = parse_solution_ds1000_gpt(sample_text)
    if solution:
        print("Extracted solution:")
        print_success("\n" + solution)
    else:
        print_error("No solution found in the text.")

if __name__ == "__main__":
    main()