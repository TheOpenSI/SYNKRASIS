from typing import *

class Solution:
    def factorial(self, n: int) -> int:
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result

if __name__ == '__main__':
    import json, sys
    _args = [json.loads(line) for line in sys.stdin.read().splitlines()]
    _result = Solution().factorial(*_args)
    print(json.dumps(_result))
