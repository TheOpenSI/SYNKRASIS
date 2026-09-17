import json

from code_parser import CodeParser

SAMPLE_CODE = """
def sum_list(nums: list[int]) -> int:
    total = 0
    for n in nums:
        total += double(n)
    return total
"""


def main() -> None:
    parser = CodeParser()
    structure = parser.parse(SAMPLE_CODE)
    print(json.dumps(structure, indent=2))


if __name__ == "__main__":
    main()
