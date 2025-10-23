import time           
class GoalGeneration:
    def __init__(self):
        pass
    def generate_goal(self, primary_goal, context, llm):
        prompt = f"""
        You are a goal creation agent for Agentic Enterprise Environment
        You will be provided with a goal template and the context
        - Use the context to fill ALL THE DETAILS for every placeholder in the goal template.
        - For Create(Create, Register), Update(Update, Edit) based tasks for email and message, generate message text or email body and subject respectively. 
        # Input:
        goal_template: {primary_goal}
        context: {context}
        
        # Output Format: 
        OUTPUT JUST THE GOAL STRING
       
        """
        response = llm.gpt(prompt)
        return response
    
    
class SubgoalGeneration:
    """
    SQL Generation module with DSPy optimization.

    This class handles the generation of SQL queries from natural language queries
    using DSPy's optimized language models.

    Attributes:
        config (PromptConfig): Configuration object containing prompt templates and examples.
        nl_to_sql (NLToSQL): The initialized natural language to SQL conversion module.
    """

    def __init__(self):
        """
        Initialize the SQL generation module with configurations from a YAML file.

        Args:
            prompt_config (PromptConfig): Configuration object containing settings from YAML.
        """
        pass
    
    def generate_subgoal(self, primary_goal, tool_dependencies, context, llm):
        """
        Generate an optimized prompt for the specified task description.

        This method creates and optionally optimizes a prompt based on the task description.

        Args:
            task_description (str): Description of the task for which to generate a prompt.
            optimize (bool): Whether to optimize the prompt using MIPROv2.

        Returns:
            str: The generated prompt history.
        """

        prompt=f"""You are a SubGoal Generating Agent that decomposes a high-level goal into smaller, actionable subgoals.

            # Input:
            primary_goal={primary_goal}
            tool_dependencies={tool_dependencies}
            context={context}

            ## Instructions ##
            Your task is to break down the given primary goal into granular subgoals. Each subgoal must:

            - Stay strictly aligned with the original primary goal.
            - Don’t assume context is direct input
            - You have to extract the details of context (keys) using the entities in primary_goal only
            - first subgoal(s) must extract it using tools IF NECESSARY, with arguments derived from the primary_goal (emp_id is always given)
            - Don't use arguments from context, if not present in primary_goal, first use tools that can extract the necessary argument (argument type) required.
            - Map to **one** tool from the provided tool_dependencies.
            - Avoid redundancy or synthetic-sounding tasks.
            - For Create, Update tasks Use llm tool to create the arguments only if not present.

            DO NOT include subgoals that are irrelevant or too broad.
            DO NOT combine multiple tools in a single subgoal.

            # Output:
            ONLY RETURN A DICT IN BELOW FORMAT.

            Example format:
            {{
            "subgoals": [
                "Run `conversation_sentiment_analyzer` on recent customer chats to detect overall sentiment.",
                "Use the sentiment output to identify conversations with strong negative tones post-support.",
                "Call `support_interaction_analyzer` to extract patterns from those conversations involving negative experiences."
            ],
            tools:[
                {{
                    tool_name: str,
                    tool_arguments: dict,
                }},
                ...  
            ]
            }}
           
        """
        
        
        response = llm.gpt(prompt)
        return response
                        
        
class TemplateGeneration:
    """
    Query Refinement with DSPy.

    This class handles the refinement of natural language queries based on
    the query itself and chat history using DSPy's optimized language models.

    Attributes:
        prompt_config (PromptConfig): Configuration object containing prompt templates and examples.
        prompt (str): The generated prompt for query refinement.
    """

    def __init__(self):
        """
        Initialize the Query Refinement module.

        Args:
            prompt_config (PromptConfig): Configuration object containing prompt templates and examples.
        """
        self.prompt = ""

    
    def generate_template(self, subgoal, tool_context,  persona, llm):
        """
        Generate an optimized prompt for the specified task description.

        This method creates and optionally optimizes a prompt based on the task description.

        Args:
            task_description (str): Description of the task for which to generate a prompt.
            optimize (bool): Whether to optimize the prompt using MIPROv2.

        Returns:
            str: The generated prompt history.
        """

        prompt=f"""You are a Task Template Generating Agent.
            # Input:
            subgoals={subgoal}
            tool_context={tool_context}

            ## Instructions ##
            Your goal is to convert the subgoal into a natural-sounding question template that:
            - Could realistically be asked by a Domain expert with details {persona} in an enterprise setting.
            - Matches the intent of the subgoal.
            - Uses placeholders (e.g., <product>, <issue>, <device>) that correspond to elements in the provided context.
            - Is answerable using the tool mentioned in the corresponding tool dependency.

            Guidelines:
            - Use first-person phrasing as if the question is being asked directly.
            - Ensure the question naturally follows from the subgoal and reflects its purpose.
            - Each question must map clearly to one tool dependency.
            - Do not fabricate placeholders — derive them from the context.
            - Avoid overly synthetic or robotic phrasing.
            # Output:
             ONLY RETURN A DICT IN BELOW FORMAT.

            Example format:
           {{
            "template": ......,
            "tools": [
                {{
                    "tool_name": str,
                    "tool_arguments": dict,
                    "tool_output": dict
                }},
                ......
            ]
           }}
            
            
        """
        
        
        response = llm.gpt(prompt)
        return response
            
        
    
class SubTaskGeneration:
    """
    Query Refinement with DSPy.

    This class handles the refinement of natural language queries based on
    the query itself and chat history using DSPy's optimized language models.

    Attributes:
        prompt_config (PromptConfig): Configuration object containing prompt templates and examples.
        prompt (str): The generated prompt for query refinement.
    """

    def __init__(self):
        """
        Initialize the Query Refinement module.

        Args:
            prompt_config (PromptConfig): Configuration object containing prompt templates and examples.
        """
        self.prompt = ""

    
    def generate_subtask(self, primary_goal, subgoal,  template,  persona, llm):
        """
        Generate an optimized prompt for the specified task description.

        This method creates and optionally optimizes a prompt based on the task description.

        Args:
            task_description (str): Description of the task for which to generate a prompt.
            optimize (bool): Whether to optimize the prompt using MIPROv2.

        Returns:
            str: The generated prompt history.
        """

        prompt=f"""You are a Human Domain Expert tasked with curating high-quality, structured business tasks that reflect realistic analytical workflows.
            # Input:
            persona={persona}
            primary_goal={primary_goal}
            subgoal={subgoal}
            template={template}

            ## Instructions ##

            Your objective is to generate a well-structured, domain-relevant subtask that will be executed to achieve primary_goal, grounded in tool context, using the knowledge of a human domain expert.

            - Use the `subgoal` and corresponding `template` to formulate the subtask that reflects a realistic and meaningful question a **domain expert in the role described by `persona`** would ask.
            - The Don't change the intent of the primary goal.
            - Don't synthetically include terms that changes the primary_goal
            - Use the tool context that is basically the Action over the Thought (subgoal) by agent and the Observation will be a tool_output.
            ## Output Format ##
            ONLY RETURN A DICT IN BELOW FORMAT.
            {{
            "subtask": ......,
            "tools": [
                {{
                    "tool_name": str,
                    "tool_arguments": dict,
                    "tool_output": dict
                }},
                ......
            ]
           }}
        """
        response = llm.gpt(prompt)
        return response
    
class TaskGeneration:
    """
    Query Refinement with DSPy.

    This class handles the refinement of natural language queries based on
    the query itself and chat history using DSPy's optimized language models.

    Attributes:
        prompt_config (PromptConfig): Configuration object containing prompt templates and examples.
        prompt (str): The generated prompt for query refinement.
    """

    def __init__(self):
        """
        Initialize the Query Refinement module.

        Args:
            prompt_config (PromptConfig): Configuration object containing prompt templates and examples.
        """
        self.prompt = ""

    
    def generate_task(self, primary_goal, subtasks,context,  persona, llm):
        """
        Generate an optimized prompt for the specified task description.

        This method creates and optionally optimizes a prompt based on the task description.

        Args:
            task_description (str): Description of the task for which to generate a prompt.
            optimize (bool): Whether to optimize the prompt using MIPROv2.

        Returns:
            str: The generated prompt history.
        """

        prompt=f"""You are a Human Domain Expert tasked with curating high-quality, structured business tasks that reflect realistic analytical workflows.
            # Input:
            persona={persona}
            primary_goal={primary_goal}
            ground_truth_context={context}
            subtasks={subtasks}

            ## Instructions ##

            Your objective is to generate a well-structured, domain-relevant task based on subtasks, using the knowledge of a human domain expert.

            ## Guidelines:
            - Task is the agentic query that will be provided by Human to an Enterprise Agent
            - The Task is the final goal, such that if subtasks are executed in the same sequence the agent will finally achieve the task.
            - Create a ground_truth of the task for final evaluation using the outputs of each individual subtasks and ground_truth_context
            - For ground_truth of Create, Update and Delete based tasks, only incorporate the id the item to be created, updated or deleted
            
            ## Output Format ##
            ONLY RETURN A DICT IN BELOW FORMAT.
            {{
            "task": {primary_goal},
            "ground_truth": .....
           }}
        """
        response = llm.gpt(prompt)
        return response
    
class Validation:
    """
    Query Refinement with DSPy.

    This class handles the refinement of natural language queries based on
    the query itself and chat history using DSPy's optimized language models.

    Attributes:
        prompt_config (PromptConfig): Configuration object containing prompt templates and examples.
        prompt (str): The generated prompt for query refinement.
    """

    def __init__(self):
        """
        Initialize the Query Refinement module.

        Args:
            prompt_config (PromptConfig): Configuration object containing prompt templates and examples.
        """
        self.prompt = ""

    
    def validate_task(self, task, primary_goal,persona, llm):
        """
        Generate an optimized prompt for the specified task description.

        This method creates and optionally optimizes a prompt based on the task description.

        Args:
            task_description (str): Description of the task for which to generate a prompt.
            optimize (bool): Whether to optimize the prompt using MIPROv2.

        Returns:
            str: The generated prompt history.
        """

        prompt=f"""
        You are critic agent that checks the generated task string with the primary_goal
        
        # Input:
        task={task}
        primary_goal={primary_goal}
        
        # Instructions:
        Compare the task and primary_goal on below questions:
        - Q1: does task contain all the information present in the primary goal?
        - Q2: Does task has a first person language mimicing {persona}
        - Q3: Does task mimics the query that a real Human {persona} can ask an agent
        
        Only if answer to all the Questions are True, Output True else False.
         
        # Output Format:
        ONLY RETURN TRUE OR FALSE
        {{"validation_check": "True/False"}}         
        """
        
        
        response = llm.gpt(prompt)
        return response

class Improvement:
    def improve_task(self, task, primary_goal, persona, llm):
        prompt = f"""
        You are an improvement agent that improves the task string with respect to the primary_goal
        
        # Input:
        task: {task}
        primary_goal: {primary_goal}
        
        # Instructions:
        - Improve the task using the primary_goal such that answer to below questions becomes true
        - Q1: does task contain all the information present in the primary goal?
        - Q2: Does task has a first person language mimicing {persona}
        - Q3: Does task mimics the query that a real Human {persona} can ask an agent
        
        Output Format:
        ONLY RETURN THE TASK STRING
        {{"task": ...}}"""
        response = llm.gpt(prompt)
        return response