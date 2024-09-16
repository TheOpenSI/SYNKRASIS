def has_close_elements(numbers: List[float], threshold: float) -> bool:
    for i in range(len(numbers) - 1):
        if abs(numbers[i] - numbers[i + 1]) < threshold:
            return True
    return False

import time
start_time = time.time()
has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3) # returns True
has_close_elements([1.0, 2.0, 3.0], 0.5) # returns False
end_time = time.time()
print(f'Execution time: {end_time - start_time} seconds')