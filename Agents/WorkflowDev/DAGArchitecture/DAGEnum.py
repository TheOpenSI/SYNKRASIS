import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from enum import Enum

class ExecutionType(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ITERATIVE = "iterative"


class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"