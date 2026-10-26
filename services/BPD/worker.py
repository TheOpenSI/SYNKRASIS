"""
Child process of BPD.trace(): reads the request as json on stdin, prints {"trace": str | null, "error": str | null}.
mode "test": the request has code_path, test_path, test_class, test_method (a unit test, see BPD.trace_test_in_process).
It executes LLM code, so it runs with a memory cap and the parent kills it after a timeout.
"""
import json
import os
import resource
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def main() -> None:
    request = json.load(sys.stdin)
    test_mode = request.get("mode") == "test"
    if not test_mode:           # the container of a unit test task limits the memory, tensorflow needs more than 4 GB of address space
        resource.setrlimit(resource.RLIMIT_AS, (4 * 1024 ** 3, 4 * 1024 ** 3))
    sys.setrecursionlimit(5000)
    from services.BPD.bpd import BPD
    max_chars, max_steps, max_seconds = request["limits"]
    bpd = BPD(max_chars, max_steps, max_seconds)
    if test_mode:
        with open(request["code_path"], "r") as code_file, open(request["test_path"], "r") as test_file:
            trace = bpd.trace_test_in_process(code_file.read(), test_file.read(), request["test_class"], request["test_method"])
    else:
        trace = bpd.trace_in_process(request["code"], request["test_input"], request["entry_point"], request["expected"])
    print(json.dumps({"trace": trace, "error": bpd.last_error}))


if __name__ == "__main__":
    main()
