from enum import Enum


class WorkflowDevAgents(Enum):
    WORKFLOW_ANALYST = "workflow_analyst"
    DEHALLUCINATOR = "dehallucinator"
    WORKFLOW_PLANNER = "workflow_planner"
    FAULT_TOLERANCE_SPEC = "fault_tolerance_spec"
    TASK_DECOMPOSER = "task_decomposer"