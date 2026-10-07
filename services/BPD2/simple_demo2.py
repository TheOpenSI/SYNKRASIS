# The five cases of services/BPD/simple_demo.py in the compact format, next to the old size.
#   python services/BPD2/simple_demo2.py            compact trace of every case
#   python services/BPD2/simple_demo2.py --old      also print the old concise report for comparison
import os
import sys
sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import re

from services.BPD.bpd import BreakpointDebugger
from services.BPD.report import ReportConfig
from services.BPD.simple_demo import CASES
from services.BPD2.bpd2 import CompactDebugger


def approx_tokens(text: str) -> int:
    """Rough token count: words and punctuation marks."""
    return len(re.findall(r"\w+|[^\w\s]", text))


def main() -> None:
    show_old = "--old" in sys.argv
    for title, code, function, args, expected in CASES:
        old = BreakpointDebugger(ReportConfig.concise()).run(code, function, *args).text
        new = CompactDebugger().run(code, function, *args).text(expected=repr(expected))
        print("=" * 80, f"\n{title}\n" + "=" * 80)
        if show_old:
            print("--- old concise:\n" + old)
        print(new)
        print(f"[approx tokens: old concise {approx_tokens(old)} -> compact {approx_tokens(new)}]\n")


if __name__ == "__main__":
    main()
