"""
Subprocess entry for the BPD2 trace: reads a request (see lcb_trace2.trace_request) as json on stdin,
writes the result as json on stdout. It executes LLM code, so it runs with a memory cap and the caller
(lcb_trace2.trace_in_subprocess) kills it after a timeout.
"""
import json
import os
import resource
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def main() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024 ** 3, 4 * 1024 ** 3))
    sys.setrecursionlimit(5000)
    from services.BPD2.lcb_trace2 import trace_request
    print(json.dumps(trace_request(json.load(sys.stdin))))


if __name__ == "__main__":
    main()
