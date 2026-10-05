class LCBHarness():
    def _build_factorial_file(self, user_query: dict, llm_generated_code: str) -> None:
        func_name = user_query["entry_point"]
        main_block = (
            "\n\n"
            "if __name__ == '__main__':\n"
            "    import json, sys\n"
            "    _args = [json.loads(line) for line in sys.stdin.read().splitlines()]\n"
            f"    _result = Solution().{func_name}(*_args)\n"
            "    print(json.dumps(_result))\n"
        )

        return "from typing import *\n\n" + llm_generated_code + main_block