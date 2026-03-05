from __future__ import annotations

import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from pydantic import BaseModel, model_validator

from Agents.WorkflowDev.DAGArchitecture.DAGEnum import ExecutionType


class TaskSpec(BaseModel):
    id: str
    description: str
    phase: str
    execution_type: ExecutionType
    depends_on: list[str]
    consumes: str
    produces: str
    parallel_group: str | None


class PhaseSpec(BaseModel):
    phase_id: str
    phase_name: str
    description: str
    task_ids: list[str]


class WorkflowPlannerOutput(BaseModel):
    process_name: str
    phases: list[PhaseSpec]
    tasks: list[TaskSpec]

    @model_validator(mode="after")
    def validate_phase_task_ids_exist(self) -> WorkflowPlannerOutput:
        """Ensure every task_id referenced in phases exists in the task list."""
        task_ids = {t.id for t in self.tasks}
        for phase in self.phases:
            for tid in phase.task_ids:
                if tid not in task_ids:
                    raise ValueError(
                        f"Phase '{phase.phase_id}' references task '{tid}' "
                        f"which does not exist in the task list."
                    )
        return self
