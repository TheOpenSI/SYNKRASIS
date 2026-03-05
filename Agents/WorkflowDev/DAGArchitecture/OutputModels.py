import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from pydantic import BaseModel
from typing import Union

from Agents.WorkflowDev.DAGArchitecture.DAGEnum import ExecutionType, ValidationSeverity
from Agents.WorkflowDev.DAGArchitecture.InputModels import PhaseSpec

class ValidationIssue(BaseModel):
    severity: ValidationSeverity
    check: str
    message: str


class ValidationReport(BaseModel):
    passed: bool
    issues: list[ValidationIssue]


class DAGNode(BaseModel):
    id: str
    description: str
    phase: str
    execution_type: ExecutionType
    depends_on: list[str]
    consumes: str
    produces: str
    parallel_group: Union[str, None]


class DAGOutput(BaseModel):
    process_name: str
    validation_report: ValidationReport
    phases: list[PhaseSpec]
    nodes: list[DAGNode]
    adjacency_list: dict[str, list[str]]
    entry_points: list[str]
    terminal_nodes: list[str]
    parallel_groups: dict[str, list[str]]