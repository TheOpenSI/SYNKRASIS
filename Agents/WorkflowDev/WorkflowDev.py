# =======================================================================================================
# WorkflowDev: A multi-agent system for generating fault-tolerant DAGs and task decompositions from BRDs.
# Usage:
#   - get_dag(dag_visualisation_output_path: str) -> dict: 
#     Orchestrates the full pipeline and returns the task decomposition.
# =======================================================================================================

from __future__ import annotations

import json
import os
import re
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from services.LLM.LLMBase import LLMBase

from services.LLM.OpenAI_GPT.OpenAI_GPT import OpenAI_GPT
from Agents.WorkflowDev.WorkflowDevAgentsEnum import WorkflowDevAgents
from Agents.WorkflowDev.DAGArchitecture.InputModels import WorkflowPlannerOutput
from Agents.WorkflowDev.DAGArchitecture.DAGArchitect import DAGArchitect, DAGValidationError
from Agents.WorkflowDev.DAGVisualiser import DAGVisualiser, VisualiserConfig
from utils.logger.Logger import Logger


class WorkflowDev:
    def __init__(self, 
                 brd_path: str) -> None:
        """
        WorkflowDev orchestrates a multi-agent planning pipeline to generate a fault-tolerant DAG and 
        task decomposition from a Business Requirements Document (BRD).

        Args:
            brd_path (str): File path to the Business Requirements Document.
        """
        self.logger = Logger(__class__.__name__, "DEBUG")
        # Business Requirements Document
        self.brd_content = "Business Requirements Document:\n" + self._load_content(brd_path)
        self.logger.info(f"Loaded BRD content from {brd_path}")

        # Runtime prompts for the dehallucinator
        self.dehall_rt_workflow_analyst = self._load_content(
            "Agents/WorkflowDev/prompts/rt_dehallucination/rt_workflow_analyst.txt"
        )
        self.logger.info("Loaded dehallucinator runtime prompt for Workflow Analyst")
        
        self.dehall_rt_workflow_planner = self._load_content(
            "Agents/WorkflowDev/prompts/rt_dehallucination/rt_workflow_planner.txt"
        )
        self.logger.info("Loaded dehallucinator runtime prompt for Workflow Planner")
        
        self.dehall_rt_fault_tolerance_spec = self._load_content(
            "Agents/WorkflowDev/prompts/rt_dehallucination/rt_fault_tolerance_spec.txt"
        )
        self.logger.info("Loaded dehallucinator runtime prompt for Fault Tolerance Spec")

        # LLM agents
        self.workflow_analyst: LLMBase = OpenAI_GPT(model_name="gpt-4.1-2025-04-14")
        self.workflow_planner: LLMBase = OpenAI_GPT(model_name="gpt-4.1-2025-04-14")
        self.fault_tolerance_spec: LLMBase = OpenAI_GPT(model_name="gpt-4.1-2025-04-14")
        self.task_decomposer: LLMBase = OpenAI_GPT(model_name="gpt-4.1-2025-04-14")
        self.dehallucinator: LLMBase = OpenAI_GPT(model_name="gpt-4.1-2025-04-14")

        # System prompts
        self.workflow_analyst.set_system_prompt_from_file(
            "Agents/WorkflowDev/prompts/workflow_analyst.txt"
        )
        self.workflow_planner.set_system_prompt_from_file(
            "Agents/WorkflowDev/prompts/workflow_planner.txt"
        )
        self.fault_tolerance_spec.set_system_prompt_from_file(
            "Agents/WorkflowDev/prompts/fault_tolerance_spec.txt"
        )
        self.task_decomposer.set_system_prompt_from_file(
            "Agents/WorkflowDev/prompts/task_decomposer.txt"
        )
        self.dehallucinator.set_system_prompt_from_file(
            "Agents/WorkflowDev/prompts/dehallucination.txt"
        )
        self.logger.info("All system prompts loaded and set for agents.")


    def _load_content(self, file_path: str) -> str:
        """
        Load content from a file.

        Args:
            file_path (str): Path to the file.

        Returns:
            str: Content of the file.
        """
        with open(file_path, "r") as file:
            return file.read()


    def _extract_json(self, response: str) -> dict:
        """
        Extract and parse a JSON block from an LLM response.

        Handles responses where JSON is wrapped in markdown code fences
        as well as responses that are raw JSON.

        Args:
            response (str): Raw LLM response string.

        Returns:
            dict: Parsed JSON as a Python dictionary.

        Raises:
            ValueError: If no valid JSON block can be found or parsed.
        """
        self.logger.info("Extracting JSON from LLM response...")
        # Strip markdown code fences if present
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
        candidate = fenced.group(1).strip() if fenced else response.strip()

        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            self.logger.error(f"Failed to parse JSON from LLM response: {exc}")
            raise ValueError(
                f"Failed to parse JSON from LLM response: {exc}\n"
                f"Candidate string:\n{candidate}"
            )


    def _get_runtime_prompt(self, agent: WorkflowDevAgents) -> str:
        """
        Get the dehallucinator runtime prompt for a specific agent.

        Args:
            agent (WorkflowDevAgents): The agent enum.

        Returns:
            str: The runtime prompt.

        Raises:
            ValueError: If the agent does not have a runtime prompt.
        """
        runtime_prompts = {
            WorkflowDevAgents.WORKFLOW_ANALYST: self.dehall_rt_workflow_analyst,
            WorkflowDevAgents.WORKFLOW_PLANNER: self.dehall_rt_workflow_planner,
            WorkflowDevAgents.FAULT_TOLERANCE_SPEC: self.dehall_rt_fault_tolerance_spec,
        }
        self.logger.info(f"Retrieving runtime prompt for agent: {agent.value}")

        if agent not in runtime_prompts:
            self.logger.error(f"No runtime prompt registered for agent: {agent}")
            raise ValueError(f"No runtime prompt registered for agent: {agent}")

        return runtime_prompts[agent]


    def _dehallucinator(self, 
                        response: str, 
                        agent_code: WorkflowDevAgents) -> str:
        """
        Run the dehallucinator against an agent's response to produce scrutiny feedback.

        Args:
            response (str): The agent response to scrutinise.
            agent_code (WorkflowDevAgents): The agent whose output is being reviewed.

        Returns:
            str: Structured scrutiny feedback for refinement.
        """
        self.logger.info(f"Running dehallucinator/refining for agent: {agent_code.value}")
        runtime_prompt = self._get_runtime_prompt(agent_code)
        context = (
            self.brd_content + "\n\n" +
            f"{agent_code.value.upper()} Agent's Response to Review:\n" +
            response + "\n\n" +
            "Your Instructions:\n" +
            runtime_prompt
        )
        return self.dehallucinator.generate_response(context)


    def _single_round_refinement(self,
                                 agent: LLMBase,
                                 agent_original_response: str,
                                 feedback: str) -> str:
        """
        Perform a single round of refinement using dehallucinator feedback.

        # NOTE: ChatDev dehallucinator pattern, single refinement iteration.

        Args:
            agent (LLMBase): The agent to perform the refinement.
            agent_original_response (str): The agent's initial response.
            feedback (str): Scrutiny feedback from the dehallucinator.

        Returns:
            str: The refined agent response.
        """
        context = (
            "Input BRD:\n" +
            self.brd_content + "\n\n" +
            "Your Previous Response:\n" +
            agent_original_response + "\n\n" +
            "Feedback for Refinement:\n" +
            feedback + "\n\n" +
            "Please refine your previous response based on the feedback provided."
        )
        return agent.generate_response(context)


    def _workflow_analyst(self, 
                          dehallucinator_response: str = None) -> str:
        """
        Generate a structured process specification from the BRD.

        Args:
            dehallucinator_response (str, optional): Scrutiny feedback for refinement.

        Returns:
            str: Workflow analysis response containing a JSON process specification.
        """
        self.logger.info("Generating workflow analysis response...")
        if dehallucinator_response:
            context = (
                self.brd_content + "\n\n" +
                "The project manager requested some clarifications. "
                "Please address the following:\n" +
                dehallucinator_response
            )
        else:
            context = self.brd_content

        return self.workflow_analyst.generate_response(context)


    def _workflow_planner(self,
                          workflow_analyst_output: str,
                          dehallucinator_response: str = None) -> str:
        """
        Enrich the validated task specification with execution metadata.

        Args:
            workflow_analyst_output (str): Refined JSON output from the workflow analyst.
            dehallucinator_response (str, optional): Scrutiny feedback for refinement.

        Returns:
            str: Workflow planner response containing an enriched JSON specification.
        """
        self.logger.info("Generating workflow planner response...")
        if dehallucinator_response:
            context = (
                "Workflow Analyst Specification:\n" +
                workflow_analyst_output + "\n\n" +
                "Feedback for Refinement:\n" +
                dehallucinator_response + "\n\n" +
                "Please refine your previous response based on the feedback provided."
            )
        else:
            context = (
                "Workflow Analyst Specification:\n" +
                workflow_analyst_output
            )

        return self.workflow_planner.generate_response(context)


    def _fault_tolerance_spec(self,
                              dag_output: str,
                              dehallucinator_response: str = None) -> str:
        """
        Annotate each DAG node with fault tolerance attributes.

        Args:
            dag_output (str): JSON-serialised DAGOutput from the DAG Architect.
            dehallucinator_response (str, optional): Scrutiny feedback for refinement.

        Returns:
            str: Fault tolerance specification response containing an annotated JSON.
        """
        self.logger.info("Generating fault tolerance specification response...")
        if dehallucinator_response:
            context = (
                self.brd_content + "\n\n" +
                "DAG Specification:\n" +
                dag_output + "\n\n" +
                "Feedback for Refinement:\n" +
                dehallucinator_response + "\n\n" +
                "Please refine your previous response based on the feedback provided."
            )
        else:
            context = (
                self.brd_content + "\n\n" +
                "DAG Specification:\n" +
                dag_output
            )

        return self.fault_tolerance_spec.generate_response(context)


    def _task_decomposer(self, fault_tolerance_output: str) -> str:
        """
        Translate the fault-tolerant DAG into self-contained coding specifications.

        Args:
            fault_tolerance_output (str): JSON-serialised fault tolerance specification.

        Returns:
            str: Task decomposer response containing per-task coding specifications.
        """
        self.logger.info("Generating task decomposition response...")
        context = (
            self.brd_content + "\n\n" +
            "Fault Tolerance Specification:\n" +
            fault_tolerance_output
        )
        return self.task_decomposer.generate_response(context)


    def _run_dag_architect(self, workflow_planner_output: str) -> tuple[str, object]:
        """
        Parse the workflow planner output and construct a validated DAG.

        Args:
            workflow_planner_output (str): Raw LLM response from the workflow planner.

        Returns:
            tuple[str, DAGOutput]: JSON-serialised DAGOutput and the DAGOutput object.

        Raises:
            ValueError: If the workflow planner output cannot be parsed as valid JSON.
            DAGValidationError: If the constructed DAG fails structural validation.
        """
        self.logger.info("Running DAG Architect to construct and validate DAG...")
        planner_json = self._extract_json(workflow_planner_output)
        planner_output = WorkflowPlannerOutput(**planner_json)

        architect = DAGArchitect(planner_output)
        dag_output = architect.build()

        return dag_output.model_dump_json(indent=2), dag_output


    def _run_dag_visualiser(self, fault_tolerance_output: str, output_path: str) -> None:
        """
        Render the fault-tolerant DAG as a PNG visualisation.

        Args:
            fault_tolerance_output (str): Raw LLM response from the fault tolerance agent.
            output_path (str): File path to save the rendered PNG.

        Returns:
            None

        Raises:
            ValueError: If the fault tolerance output cannot be parsed as valid JSON.
        """
        self.logger.info("Running DAG Visualiser to render DAG visualisation...")
        ft_json = self._extract_json(fault_tolerance_output)
        config = VisualiserConfig(output_path=output_path)
        visualiser = DAGVisualiser(ft_json, config)
        visualiser.render()


    def get_dag(self, 
                visualisation_output_path: str = "dag_output.png") -> dict:
        """
        Orchestrate the full planning pipeline and return the task decomposition.

        Pipeline stages:
            1. Workflow Analyst  -> Dehallucinator -> Single round refinement
            2. Workflow Planner  -> Dehallucinator -> Single round refinement
            3. DAG Architect (deterministic)
            4. Fault Tolerance Spec -> Dehallucinator -> Single round refinement
            5. DAG Visualiser (deterministic)
            6. Task Decomposer

        Args:
            visualisation_output_path (str): File path to save the DAG visualisation PNG.

        Returns:
            dict: Parsed task decomposition JSON from the Task Decomposer.

        Raises:
            ValueError: If any LLM response cannot be parsed to the expected JSON structure.
            DAGValidationError: If the DAG fails structural validation.
        """
        os.makedirs(os.path.dirname(visualisation_output_path), exist_ok=True)
        
        # Stage 1: Workflow Analyst
        print("[1/6] Workflow Analyst running...")
        wa_response = self._workflow_analyst()

        print("[1/6] Dehallucinating workflow analyst output...")
        wa_feedback = self._dehallucinator(
            response=wa_response,
            agent_code=WorkflowDevAgents.WORKFLOW_ANALYST
        )

        print("[1/6] Refining workflow analyst output...")
        wa_refined = self._single_round_refinement(
            agent=self.workflow_analyst,
            agent_original_response=wa_response,
            feedback=wa_feedback
        )

        # Stage 2: Workflow Planner
        print("[2/6] Workflow Planner running...")
        wp_response = self._workflow_planner(workflow_analyst_output=wa_refined)

        print("[2/6] Dehallucinating workflow planner output...")
        wp_feedback = self._dehallucinator(
            response=wp_response,
            agent_code=WorkflowDevAgents.WORKFLOW_PLANNER
        )

        print("[2/6] Refining workflow planner output...")
        wp_refined = self._workflow_planner(
            workflow_analyst_output=wa_refined,
            dehallucinator_response=wp_feedback
        )

        # Stage 3: DAG Architect (deterministic)
        print("[3/6] DAG Architect constructing and validating DAG...")
        dag_output_json, dag_output = self._run_dag_architect(wp_refined)
        print(f"[3/6] DAG validated. "
              f"Entry points: {dag_output.entry_points} | "
              f"Terminal nodes: {dag_output.terminal_nodes}")

        # Stage 4: Fault Tolerance Specification
        print("[4/6] Fault Tolerance Specification running...")
        ft_response = self._fault_tolerance_spec(dag_output=dag_output_json)

        # print("[4/6] Dehallucinating fault tolerance output...")
        # ft_feedback = self._dehallucinator(
        #     response=ft_response,
        #     agent_code=WorkflowDevAgents.FAULT_TOLERANCE_SPEC
        # )

        # print("[4/6] Refining fault tolerance output...")
        # ft_refined = self._fault_tolerance_spec(
        #     dag_output=dag_output_json,
        #     dehallucinator_response=ft_feedback
        # )

        # Stage 5: DAG Visualiser (deterministic)
        print("[5/6] DAG Visualiser rendering...")
        self._run_dag_visualiser(
            fault_tolerance_output=ft_response,
            output_path=visualisation_output_path
        )

        # Stage 6: Task Decomposer
        print("[6/6] Task Decomposer running...")
        td_response = self._task_decomposer(fault_tolerance_output=ft_response)
        task_decomposition = self._extract_json(td_response)

        print("[6/6] Planning pipeline complete.")
        self.logger.info("Planning pipeline complete. Returning task decomposition.")
        return task_decomposition


if __name__ == "__main__":
    brd_path = "Agents/WorkflowDev/BRD/customer_churn.txt"

    workflow_dev = WorkflowDev(brd_path=brd_path)
    result = workflow_dev.get_dag(visualisation_output_path="Agents/WorkflowDev/DAG/dag_output.png")

    print(json.dumps(result, indent=2))