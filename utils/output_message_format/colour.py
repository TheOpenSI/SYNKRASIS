from enum import Enum

class Colour(Enum):
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    RESET = "\033[0m"
    BRIGHT_RED = "\033[91m"

# --------------------------------------------------------------------------
# example
# print(f"{Color.RED.value}[ERROR]{Color.RESET.value} Something went wrong!")
# --------------------------------------------------------------------------