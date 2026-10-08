"""
Child process of BPD.trace(): reads the request as json on stdin, prints {"trace": str | null, "error": str | null}.
It executes LLM code, so it runs with a memory cap and the parent kills it after a timeout.
"""
import json
import os
import resource
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def main() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024 ** 3, 4 * 1024 ** 3))
    sys.setrecursionlimit(5000)
    from services.BPD.bpd import BPD
    request = json.load(sys.stdin)
    max_chars, max_steps, max_seconds = request["limits"]
    bpd = BPD(max_chars, max_steps, max_seconds)
    trace = bpd.trace_in_process(request["code"], request["test_input"], request["entry_point"], request["expected"])
    print(json.dumps({"trace": trace, "error": bpd.last_error}))


if __name__ == "__main__":
    main()
