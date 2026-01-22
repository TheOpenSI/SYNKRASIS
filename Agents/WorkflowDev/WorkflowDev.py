import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from services.LLM.LLMBase import LLMBase

from services.LLM.Ollama.OllamaClient import OllamaClient
from services.LLM.OpenAI_GPT.OpenAI_GPT import OpenAI_GPT

class WorkflowDev:
    def __init__(self,
                 brd_path: str) -> None:
        # Business Requirement Document path
        self.brd_path = brd_path
        with open(self.brd_path, 'r') as brd_file:
            self.brd_content = brd_file.read()
        
        # # requirements analyst
        # self.requirement_analyst: LLMBase = OllamaClient(model_name="qwen2.5-coder:latest",
        #                                         container_name="localhost",
        #                                         enable_chat_history=True,
        #                                         max_history=1)
        # # dehallucinator
        # self.dehallucinator: LLMBase = OllamaClient(model_name="qwen2.5-coder:latest",
        #                                       container_name="localhost")
        # # task decomposer
        # self.task_decomposer: LLMBase = OllamaClient(model_name="qwen2.5-coder:latest",
        #                                     container_name="localhost")
        
        # requirements analyst
        self.requirement_analyst: LLMBase = OpenAI_GPT(model_name="gpt-4.1-2025-04-14",
                                                enable_chat_history=True,
                                                max_history=1)
        # dehallucinator
        self.dehallucinator: LLMBase = OpenAI_GPT(model_name="gpt-4.1-2025-04-14")
        # task decomposer
        self.task_decomposer: LLMBase = OpenAI_GPT(model_name="gpt-4.1-2025-04-14")
        
        # system prompts
        self.requirement_analyst.set_system_prompt_from_file("Agents/WorkflowDev/prompts/requirement_analyst.txt")
        self.dehallucinator.set_system_prompt_from_file("Agents/WorkflowDev/prompts/dehallucination.txt")
        self.task_decomposer.set_system_prompt_from_file("Agents/WorkflowDev/prompts/task_decomposer.txt")


    def _requirement_analyst(self, 
                             dehallucinator_response: str = None) -> str:
        if dehallucinator_response:
            rq_context = (self.brd_content + "\n\n" +
                          "The project manager requested some clarifications. " +
                          "Please address the following:\n" +
                          dehallucinator_response)
        else:
            rq_context = self.brd_content
            
        return self.requirement_analyst.generate_response(rq_context)
    
    
    def _dehallucinator(self,
                        response: str) -> str:
        dehallucination_context = (self.brd_content + "\n\n" +
                                   "Analysis:\n" +
                                   response)
        return self.dehallucinator.generate_response(dehallucination_context)
    
    
    def get_dag(self) -> str:
        """
        NOTE: ChatDev dehallucinator pattern, single refinement iteration.
        """
        initial_rq = self._requirement_analyst()
        dehallucination = self._dehallucinator(initial_rq)
        refined_rq = self._requirement_analyst(dehallucinator_response=dehallucination)
        
        return refined_rq
        
        

if __name__ == "__main__":
    brd_path = "Agents/WorkflowDev/BRD/customer_churn_business_requirement_document.txt"
    
    workflow_dev = WorkflowDev(brd_path=brd_path)
    workflow_dev.get_dag()