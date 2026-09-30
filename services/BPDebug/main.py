import sys
import os
import pprint

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from TraceCollector import TraceCollector
from TraceAnalyser import TraceAnalyser
from trace_summariser import TraceSummariser
from trace_formatter import TraceFormatter
from tests.test_functions import (
    factorial,
    sum_list,
    sum_list_with_exception,
    recursive_with_loop,
)


collector  = TraceCollector()
analyser   = TraceAnalyser()
summariser = TraceSummariser()
formatter  = TraceFormatter()


def run_case(label: str, 
             func: callable, 
             *args) -> None:
    print("=" * 80)
    print(label)
    print("=" * 80)
    result, log = collector.run(func, *args)
    roots = analyser.analyse(log)
    summaries = [summariser.summarise(root) for root in roots]

    print("--- formatted prompt ---")
    for summary in summaries:
        print(formatter.format(summary))

    print()
    print("--- summary dict ---")
    pprint.pprint(summaries, sort_dicts=False)
    print(f"\nResult: {result}\n")


run_case("FACTORIAL(4) — recursive",                     factorial,               4)
# run_case("SUM_LIST([1,2,3,4]) — loop with helper",       sum_list,                [1, 2, 3, 4])
# run_case("SUM_LIST_WITH_EXCEPTION([1,0,3]) — exception", sum_list_with_exception, [1, 0, 3])
# run_case("RECURSIVE_WITH_LOOP(3) — mixed",               recursive_with_loop,     3)