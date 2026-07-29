import os, sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

from services.BPD.TraceCollector import TraceCollector
from services.BPD.tests.test_functions import (
    factorial,
    sum_list,
    sum_list_with_exception,
    recursive_with_loop,
)

if __name__ == "__main__":
    collector  = TraceCollector()
    result, logs = collector.run(sum_list, [1, 2, 3, 4, 5])
    
    for log in logs:
        print(log)