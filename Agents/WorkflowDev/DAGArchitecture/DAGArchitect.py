from __future__ import annotations

import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import networkx as nx

from Agents.WorkflowDev.DAGArchitecture.DAGEnum import ExecutionType, ValidationSeverity
from Agents.WorkflowDev.DAGArchitecture.InputModels import WorkflowPlannerOutput, PhaseSpec, TaskSpec
from Agents.WorkflowDev.DAGArchitecture.OutputModels import DAGNode, DAGOutput, ValidationIssue, ValidationReport
from Agents.WorkflowDev.DAGArchitecture.DAGValidationError import DAGValidationError


class DAGArchitect:
    """Constructs and validates a Directed Acyclic Graph from a Workflow Planner output.

    Takes the enriched task specification produced by the Workflow Planner and
    mechanically constructs a NetworkX DiGraph. Runs a suite of validation checks
    and produces a formal DAG representation for downstream agents.

    Args:
        planner_output (WorkflowPlannerOutput): The validated output from the
            Workflow Planner agent.

    Raises:
        ValueError: If the planner output fails structural validation during
            model initialisation.
    """

    def __init__(self, planner_output: WorkflowPlannerOutput) -> None:
        self._planner_output = planner_output
        self._graph: nx.DiGraph = nx.DiGraph()
        self._issues: list[ValidationIssue] = []
        self._task_map: dict[str, TaskSpec] = {
            t.id: t for t in planner_output.tasks
        }
        

    def build(self) -> DAGOutput:
        """Build and validate the DAG from the Workflow Planner output.

        Constructs the graph, runs all validation checks, and returns a complete
        DAG output including the validation report and formal graph representation.

        Returns:
            DAGOutput: The formal DAG representation with validation report,
                adjacency list, entry points, terminal nodes, and parallel groups.

        Raises:
            DAGValidationError: If any ERROR-severity validation checks fail.
        """
        self._build_graph()
        self._validate_references()
        self._validate_cycles()
        self._validate_parallel_groups()
        self._validate_connectivity()

        errors = [i for i in self._issues if i.severity == ValidationSeverity.ERROR]
        if errors:
            messages = "\n".join(f"  [{i.check}] {i.message}" for i in errors)
            raise DAGValidationError(
                f"DAG validation failed with {len(errors)} error(s):\n{messages}"
            )

        return DAGOutput(
            process_name=self._planner_output.process_name,
            validation_report=ValidationReport(
                passed=not errors,
                issues=self._issues,
            ),
            phases=self._planner_output.phases,
            nodes=self._build_nodes(),
            adjacency_list=self._build_adjacency_list(),
            entry_points=self._get_entry_points(),
            terminal_nodes=self._get_terminal_nodes(),
            parallel_groups=self._build_parallel_groups(),
        )


    def _build_graph(self) -> None:
        """Construct the NetworkX DiGraph from tasks and their dependencies.

        Each task becomes a node carrying its full metadata as attributes.
        Each depends_on relationship becomes a directed edge from dependency
        to dependent (T1 -> T2 means T2 depends on T1).

        Returns:
            None
        """
        for task in self._planner_output.tasks:
            self._graph.add_node(task.id, **task.model_dump())

        for task in self._planner_output.tasks:
            for dependency_id in task.depends_on:
                self._graph.add_edge(dependency_id, task.id)


    def _build_nodes(self) -> list[DAGNode]:
        """Convert the internal task map into a list of DAGNode output models.

        Returns:
            list[DAGNode]: Ordered list of DAG nodes matching the task list order.
        """
        return [
            DAGNode(**task.model_dump())
            for task in self._planner_output.tasks
        ]


    def _build_adjacency_list(self) -> dict[str, list[str]]:
        """Build a plain adjacency list from the NetworkX graph.

        Returns:
            dict[str, list[str]]: Mapping of each task ID to the list of task
                IDs that depend on it (i.e. its successors in the graph).
        """
        return {node: list(self._graph.successors(node)) for node in self._graph.nodes}


    def _build_parallel_groups(self) -> dict[str, list[str]]:
        """Collect tasks into their parallel groups.

        Returns:
            dict[str, list[str]]: Mapping of parallel group label to the list
                of task IDs in that group. Tasks with no parallel group are excluded.
        """
        groups: dict[str, list[str]] = {}
        for task in self._planner_output.tasks:
            if task.parallel_group is not None:
                groups.setdefault(task.parallel_group, []).append(task.id)
        return groups


    def _get_entry_points(self) -> list[str]:
        """Identify tasks with no dependencies (roots of the DAG).

        Returns:
            list[str]: Task IDs that have no incoming edges.
        """
        return [n for n in self._graph.nodes if self._graph.in_degree(n) == 0]


    def _get_terminal_nodes(self) -> list[str]:
        """Identify tasks that nothing depends on (leaves of the DAG).

        Returns:
            list[str]: Task IDs that have no outgoing edges.
        """
        return [n for n in self._graph.nodes if self._graph.out_degree(n) == 0]


    def _validate_references(self) -> None:
        """Check that every task ID in depends_on exists in the task list.

        Flags an ERROR for each dependency reference that cannot be resolved
        to a known task ID.

        Returns:
            None
        """
        for task in self._planner_output.tasks:
            for dependency_id in task.depends_on:
                if dependency_id not in self._task_map:
                    self._issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        check="reference_integrity",
                        message=(
                            f"Task '{task.id}' depends on '{dependency_id}' "
                            f"which does not exist in the task list."
                        ),
                    ))


    def _validate_cycles(self) -> None:
        """Detect cycles in the graph using NetworkX.

        A cyclic dependency means the graph is not a DAG. Each cycle found
        is reported as an ERROR.

        Returns:
            None
        """
        try:
            cycles = list(nx.simple_cycles(self._graph))
        except Exception as exc:
            self._issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                check="cycle_detection",
                message=f"Cycle detection failed with an unexpected error: {exc}",
            ))
            return

        for cycle in cycles:
            self._issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                check="cycle_detection",
                message=f"Cycle detected: {' -> '.join(cycle)} -> {cycle[0]}",
            ))


    def _validate_parallel_groups(self) -> None:
        """Validate the internal consistency of each parallel group.

        Checks two rules:
        - Tasks in the same parallel group must not depend on each other.
        - Tasks in the same parallel group must belong to the same phase.

        Returns:
            None
        """
        groups = self._build_parallel_groups()

        for group_label, task_ids in groups.items():
            self._check_intra_group_dependencies(group_label, task_ids)
            self._check_intra_group_phases(group_label, task_ids)


    def _check_intra_group_dependencies(
        self, group_label: str, task_ids: list[str]
    ) -> None:
        """Check that no task in a parallel group depends on another in the same group.

        Args:
            group_label (str): The parallel group identifier.
            task_ids (list[str]): The task IDs belonging to this group.

        Returns:
            None
        """
        task_id_set = set(task_ids)
        for task_id in task_ids:
            task = self._task_map.get(task_id)
            if task is None:
                continue
            for dependency_id in task.depends_on:
                if dependency_id in task_id_set:
                    self._issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        check="parallel_group_consistency",
                        message=(
                            f"Parallel group '{group_label}': task '{task_id}' "
                            f"depends on '{dependency_id}' which is in the same group. "
                            f"Tasks in a parallel group must not depend on each other."
                        ),
                    ))


    def _check_intra_group_phases(
        self, group_label: str, task_ids: list[str]
    ) -> None:
        """Check that all tasks in a parallel group belong to the same phase.

        Args:
            group_label (str): The parallel group identifier.
            task_ids (list[str]): The task IDs belonging to this group.

        Returns:
            None
        """
        phases = {
            self._task_map[tid].phase
            for tid in task_ids
            if tid in self._task_map
        }
        if len(phases) > 1:
            self._issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                check="parallel_group_consistency",
                message=(
                    f"Parallel group '{group_label}' spans multiple phases: "
                    f"{', '.join(sorted(phases))}. All tasks in a parallel group "
                    f"must belong to the same phase."
                ),
            ))


    def _validate_connectivity(self) -> None:
        """Check that the graph has at least one entry point and one terminal node.

        Also raises a WARNING for any task that has no dependencies and is not
        the only task in the graph, as this may indicate a disconnected subgraph.

        Returns:
            None
        """
        entry_points = self._get_entry_points()
        terminal_nodes = self._get_terminal_nodes()

        if not entry_points:
            self._issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                check="connectivity",
                message="No entry point found. At least one task must have no dependencies.",
            ))

        if not terminal_nodes:
            self._issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                check="connectivity",
                message="No terminal node found. At least one task must have no dependents.",
            ))

        if len(self._planner_output.tasks) > 1 and len(entry_points) > 1:
            self._issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                check="connectivity",
                message=(
                    f"Multiple entry points detected: {entry_points}. "
                    f"This may indicate disconnected subgraphs. Verify this is intentional."
                ),
            ))