import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

class DAGValidationError(Exception):
    """Raised when the DAG fails one or more ERROR-severity validation checks."""
    pass