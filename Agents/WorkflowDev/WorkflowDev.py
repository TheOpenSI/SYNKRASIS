from __future__ import annotations

import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from services.LLM.LLMBase import LLMBase

from services.LLM.Ollama.OllamaClient import OllamaClient
from services.LLM.OpenAI_GPT.OpenAI_GPT import OpenAI_GPT
from Agents.WorkflowDev.WorkflowDevAgents import WorkflowDevAgents

class WorkflowDev:
    def __init__(self,
                 brd_path: str) -> None:
        # Business Requirement Document path
        self.brd_content = "Business Requirements Document:\n" + self._load_content(brd_path)
            
        # dehallucination runtime prompt
        self.dehall_rt_workflow_analyst = self._load_content(
            "Agents/WorkflowDev/prompts/dehallucination/workflow_analyst.txt"
        )
        
        # OpenAI
        # workflow analyst
        self.workflow_analyst: LLMBase = OpenAI_GPT(model_name="gpt-4.1-2025-04-14")
        # dehallucinator
        self.dehallucinator: LLMBase = OpenAI_GPT(model_name="gpt-4.1-2025-04-14")
        
        # system prompts
        self.workflow_analyst.set_system_prompt_from_file(
            "Agents/WorkflowDev/prompts/workflow_analyst.txt"
            )
        self.dehallucinator.set_system_prompt_from_file(
            "Agents/WorkflowDev/prompts/dehallucination.txt"
            )
        
    
    def _load_content(self, file_path: str) -> str:
        """
        Load content from a file.
        
        Args:
            file_path (str): Path to the file.
        
        Returns:
            str: Content of the file.
        """
        with open(file_path, "r") as file:
            content = file.read()
        return content
    
    
    def _get_runtime_prompt(self, agent: WorkflowDevAgents) -> str:
        """
        Get the runtime prompt for a specific agent.
        
        Args:
            agent (WorkflowDevAgents): The agent enum.
        
        Returns:
            str: The runtime prompt.
        """
        if agent == WorkflowDevAgents.WORKFLOW_ANALYST:
            return self.dehall_rt_workflow_analyst
        else:
            raise ValueError(f"Unsupported agent: {agent}")


    def _workflow_analyst(self, 
                          dehallucinator_response: str = None) -> str:
        """
        Generate the workflow analysis based on the BRD content.
        
        Args:
            dehallucinator_response (str, optional): Clarifications from the dehallucinator
        
        Returns:
            str: Workflow analysis response, a Process Document with JSON structure.
        """
        if dehallucinator_response:
            workflow_analyst_context = (self.brd_content + "\n\n" +
                          "The project manager requested some clarifications. " +
                          "Please address the following:\n" +
                          dehallucinator_response)
        else:
            workflow_analyst_context = self.brd_content
            
        return self.workflow_analyst.generate_response(workflow_analyst_context)


    def _dehallucinator(self, 
                        response: str,
                        agent_code: WorkflowDevAgents) -> str:
        """
        Dehallucinate the workflow analysis response.
        
        Args:
            workflow_analyst_response (str): The initial workflow analysis response.
        
        Returns:
            str: Dehallucinated feedback for refinement.
        """
        runtime_prompt = self._get_runtime_prompt(agent_code)
        context = (
            "Original Input:\n" +
            self.brd_content + "\n\n" +
            "Agent Response to Review:\n" +
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
        Perform a single round of refinement using the dehallucinator.
        # NOTE: ChatDev dehallucinator pattern, single refinement iteration.
        
        Returns:
            str: The refined workflow analysis response.
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


    def get_dag(self) -> str:
        """
        Main method to get the DAG by orchestrating the agents.
        
        Returns:
            str: DAG.
        """
        workflow_analyst_response = self._workflow_analyst()
        dehallucinator_feedback = self._dehallucinator(
            response=workflow_analyst_response,
            agent_code=WorkflowDevAgents.WORKFLOW_ANALYST
        )
        refined_workflow_analyst_response = self._single_round_refinement(
            agent=self.workflow_analyst,
            agent_original_response=workflow_analyst_response,
            feedback=dehallucinator_feedback
        )


if __name__ == "__main__":
    brd_path = "Agents/WorkflowDev/BRD/customer_churn.txt"
    
    workflow_dev = WorkflowDev(brd_path=brd_path)
    workflow_dev.get_dag()