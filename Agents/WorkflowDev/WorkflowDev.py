import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from services.LLM.Ollama.OllamaClient import OllamaClient

class WorkflowDev:
    def __init__(self):
        self.requirement_analyst = OllamaClient(model_name="qwen2.5-coder:latest",
                                                container_name="localhost",
                                                enable_chat_history=True,
                                                max_history=1)
        self.dehallucinator_rq = OllamaClient(model_name="qwen2.5-coder:latest",
                                              container_name="localhost")
        self.task_decomposer = OllamaClient(model_name="qwen2.5-coder:latest",
                                            container_name="localhost")
        
        self.requirement_analyst.set_system_prompt_from_file("Agents/WorkflowDev/prompts/requirement_analyst.txt")
        self.dehallucinator_rq.set_system_prompt_from_file("Agents/WorkflowDev/prompts/dehallucination_rq.txt")
        self.task_decomposer.set_system_prompt_from_file("Agents/WorkflowDev/prompts/task_decomposer.txt")
        

if __name__ == "__main__":
    client_requirements = ("Client Requirements:\n"
                           "When a loan application comes in, check credit score. "
                           "Auto-approve if score > 700 and amount < $50k. "
                           "Send to manual review if score is 600-700. "
                           "Auto-reject if score < 600. Email customer with result.")

    workflow_dev = WorkflowDev()
    req_analyst_response = workflow_dev.requirement_analyst.generate_response(client_requirements)
    dehallucinator_rq_response = workflow_dev.dehallucinator_rq.generate_response(client_requirements + "\n\n" +
                                                                              "High-level workflow structure:\n" +
                                                                              req_analyst_response)
    
    # refined
    req_analyst_response = workflow_dev.requirement_analyst.generate_response((
                                                        "Your assistant requested some clarifications. " +
                                                        "Please provide answers to the following:\n" +
                                                        dehallucinator_rq_response))
    
    decomposed_tasks = workflow_dev.task_decomposer.generate_response(client_requirements + "\n\n" +
                                                                      req_analyst_response)