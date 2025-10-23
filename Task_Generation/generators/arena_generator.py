from Factories.llm_factory import LLM_factory
import json
from langchain_core.output_parsers import JsonOutputParser

class ArenaTasks:
    def __init__(self):
        self.llm = LLM_factory()
    def parse_json(self, json_str):
        # Remove code block markers
        if json_str.startswith("```"):
            json_str = json_str[len("```json"):].strip()
        if json_str.endswith("```"):
            json_str = json_str[:-3].strip()
        try:
            parser = JsonOutputParser()
            data = parser.parse(json_str)
            if(isinstance(data, str)):
                data = json.dump(data)
            return data
        except Exception as e:
            # print("Parsing failed:", e)
            return ""
        
        # If everything failed, give detailed error message
    def generate_task(self, task1, task2):
        create_task_prompt = f""""
        You are a Task Creation Agent for Evaluation of an Enterprise Agent, You will be provided with 2 tasks, 
        You have to combine them into multi-turn task so that the 2 tasks provided should run in some order to execute the primary task.
        
        # Inputs: 
        Task 1 : {task1}
        Task 2 : {task2}
        
        # Instructions: 
        - Keep the generated task very short and crisp and in first person language as if real Human is asking the task.
        - The task should not tool like first do this and then to that, that information should be hidden and should be extracted by the Enterprise Agent itself
        - Each input task will have a user_input, and a list of events, with event_type, tool_name, arguments, and content.
        - While generating the implicit task take into consideration of tool_call, arguments and output of that tool in content
        - Take the context of new generated task from the content of the provided tasks
        - The language of the task should not be simple such that it explicitly mentions what tool_name to call and in which order
        - Also generate a help that describes how the Enterprise Agent should execute the task with tool call, you can use thought, action and observation format for help 
        
        # Output Format:
        {{
            "task": ........
            "help": ........
        }}
        """
        
        response = self.llm.gpt(create_task_prompt)
        return response.content
    def check_relevancy(self, task1, task2):
        revelant_task_prompt = f"""
        You are a Judge Agent that takes 2 tasks as input and judges whether they can be combined into one task or not.
        
        # Inputs:
        Task 1: {task1}
        Task 2: {task2}
        
        # Instructions: 
        - You have to judge both tasks on below question:
        Q1: Can these both tasks be combined into 1 Multi-Hop Implicit task?
        Q2: Is there any relevant information in both the tasks that can be connected?
        
        Only if the Answer to both the questions is true output True else False
        If one of the task is to send a message than it can be combined with any task, return True
        # Output Format:
        {{
            "Judge": "True/False" 
        }}
        """
        response = self.llm.gpt(revelant_task_prompt)
        return response.content
    def generate(self):
        task_path = "/mnt/home-ldap/suraj_ldap/projects/Test/enterprise_data_test/single_tool_cleaned.json"
        tool_path = "/mnt/home-ldap/suraj_ldap/projects/MCP/chat/tool_schemas.json"
        data_path = "/mnt/home-ldap/suraj_ldap/projects/MCP/chat/sample_app_data.json"
        new_tasks = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Task_Generation_sft_batch2_copy/arena_tasks.json"
        with open(task_path, 'r') as f:
            tasks = json.load(f)
        with open(data_path, 'r') as f:
            data = json.load(f)
        with open(tool_path, 'r') as f:
            tools = json.load(f)
        # with open(new_tasks, 'r') as f: 
        #     created_tasks = json.load(f)
        created_tasks = []
        for i in tasks:
            for j in tasks:
                if (i==j):
                    continue
                relevency_check = self.check_relevancy(i,j)
                try:
                    relevency_check = self.parse_json(relevency_check)
                    if(relevency_check["Judge"]=="True"):
                        created_task = self.generate_task(i,j)
                        try:
                            created_task = self.parse_json(created_task)
                            created_tasks.append(created_task)
                            with open("arena_tasks_2.json", 'w') as f:
                                json.dump(created_tasks,f, indent=4)
                        except:
                            continue
                        
                except:
                    continue
                
               
                        
                        
if __name__=="__main__":
    arena_tasks = ArenaTasks()
    arena_tasks.generate()