from typing import Dict, List, Any
import json
import re

class ToolDependencyGeneration:
    """Generate tool dependencies for CRUD operations"""
    
    def generate_tool_dependencies(self, tools: List[Dict], datasource_desc, datasource_context, llm) -> str:
        """
        Generate tool dependencies for CRUD operations
        
        Args:
            tools: List of available tools and their descriptions
            context: Context data
            llm: Language model
            
        Returns:
            Tool dependencies in JSON format
        """
        prompt = f"""
            You are a database expert.

            Given the following tool/function definitions, data source descriptions, and database context, simulate what the expected output would be if the tool's/function's CRUD operations were applied to the data source context based on the return type of tool/function..

            Available tools/functions with CRUD operations:
            {json.dumps(tools, indent=2)}

            Data source description:
            {json.dumps(datasource_desc, indent=2)}

            Database context:
            {json.dumps(datasource_context, indent=2)}

            For each tool/function and its applicable CRUD operations, generate a JSON object:

            - The `tool/function` name 
            - The `operation` (Create, Read, Update, Delete)
            - The `input_requirements` (what input parameters are needed for the operation to work)
            - The `expected_output` (actual data that would result when the operation is applied to the current datasource context)

            The output format should be:
            ```json
            [
            
                "tool": "ToolName",
                "operation": "Read",
                "input_requirements": ["emp_id", "product_id"],
                "expected_output": "{{'conversations': [{{'interaction_id': 'int001', 'emp_id': 'E123', 'product_id}}}}"
            ,
            
                "tool": "ToolName",
                "operation": "Create",
                "input_requirements": ["sender_email", "recipient_email", "subject", "body"],
                "expected_output": "{{'thread_id': 'thread001', 'messages': [{{'message_id': 'msg001', 'sender_email': '}}}}"
            
            ]

        ```
        """
        
        response = llm.claude(prompt)
        return response

class SubgoalGeneration:
    """Generate subgoals for main CRUD goal"""
    
    def generate_subgoal(self, data_chain: List[str], primary_goal: str, 
                        tool_dependencies: str, datasource_desc,datasource_context, llm) -> str:
        """
        Generate subgoals to accomplish the main CRUD goal
        
        Args:
            data_chain: List of data chains
            primary_goal: Main CRUD goal
            tool_dependencies: Tool dependencies
            context: Context data
            llm: Language model
            
        Returns:
            Subgoals in JSON format
        """
        prompt = f"""
            Break down this primary CRUD goal into logical subgoals that need to be accomplished sequentially. The final result of Primary goal should be Ground Truth.

            Primary goal: {primary_goal}
            

            Data sources: {', '.join(data_chain)}

            Database description:
            {json.dumps(datasource_desc, indent=2)}

            Ground Truth:
            {json.dumps(datasource_context, indent=2)}

            Tool:
            {tool_dependencies}

            🧭 Guidelines for Breaking Down Primary Goals by CRUD Operation

            📘 If Primary Goal Operation is READ:
            - Don’t assume context is direct input; first subgoal(s) must extract it using tools IF NECESSARY, with arguments derived from the primary_goal (note: some form of ID, e.g., emp_id, product_id, or customer_id, is always given).            
            - Define what specific data is to be read and from where.
            - Apply filters, constraints, or conditions based on the goal (e.g., time range, author, type).

            🧪 If Primary Goal Operation is CREATE:
            - Don’t assume context is direct input; first subgoal(s) must extract it using tools IF NECESSARY, with arguments derived from the primary_goal (note: some form of ID, e.g., emp_id, product_id, or customer_id, is always given).
            - extract entries from the goal with LLM Call Tool (One of the Tool)
            - No need to check for duplicate entries
            - Extract content required for creation (e.g., script, record, document) from query.
            - Create the resource using the appropriate tool or endpoint.

            🛠️ If Primary Goal Operation is UPDATE:
            - Don’t assume context is direct input; first subgoal(s) must extract it using tools IF NECESSARY, with arguments derived from the primary_goal (note: some form of ID, e.g., emp_id, product_id, or customer_id, is always given).
            - extract entries from the goal with LLM Call Tool (One of the Tool)
            - No need to check for duplicate entries
            - Identify the target record or resource to be updated from the query.
            - Read the existing state if needed to determine what must change.
            - Apply the update using the tool’s supported method.

            🧹 If Primary Goal Operation is DELETE:
            - Don’t assume context is direct input; first subgoal(s) must extract it using tools IF NECESSARY, with arguments derived from the primary_goal (note: some form of ID, e.g., emp_id, product_id, or customer_id, is always given).
            - extract entries from the goal with LLM Call (One of the Tool)
            - No need to check for duplicate entries
            - Identify the entities to delete using filters or conditions.
            - Check all arguments of tool before deletion.
            - Delete the resource(s) using the appropriate operation.

            Generate a JSON array of subgoals using this structure:
            ```json
            "subtasks": [
            
                "subgoal": "First step description",
                "operation": "One of Tool",
                "expected_outcome": "Actual data that would result when the operation is applied to the current datasource context based on return type of tool/function",
                "data source": "Relevant data source for this step"
            ,
            
                "subgoal": "Second step description",
                "operation": "One of Tool",
                "expected_outcome": "Actual data that would result when the operation is applied to the current datasource context based on return type of tool/function",
                "data source": "Relevant data source for this step"
            
            ]

        ```
        """
        
        response = llm.gpt(prompt)
        return response

class TemplateGeneration:
    """Generate templates for CRUD operations"""
    
    def generate_template(self, subgoals: Dict, tool_dependencies: str, 
                         datasource_desc,datasource_context,  persona: str, llm) -> str:
        """
        Generate templates for the CRUD operations
        
        Args:
            subgoals: Subgoals for the CRUD operation
            tool_dependencies: Tool dependencies
            context: Context data
            persona: User persona
            llm: Language model
            
        Returns:
            Templates in JSON format
        """
        prompt = f"""
            You are an API design expert specializing in enterprise data operations.

            Given the following subgoals and tool/function, generate API call templates (not SQL) for achieving each subgoal using the provided tools/funtions. The final result of Primary goal should be Ground Truth.

            Subgoals:
            {json.dumps(subgoals, indent=2)}

            Tool:
            {json.dumps(tool_dependencies, indent=2)}

            Database description:
            {json.dumps(datasource_desc, indent=2)}

            Ground Truth:
            {json.dumps(datasource_context, indent=2)}

            User persona: {persona}

            For each subgoal, output:
            - The tool/function used
            - The type of operation (One of the Tool call)
            - An API template string that includes placeholders for all required inputs mentioned in Tools/functions (e.g., `/read?emp_id=<emp_id>&product_id=<product_id>`)
            - A `placeholders` object explaining each placeholder (what it means and examples of valid values)
            - Data Response in `expected_output` when this API call is executed, stick to the return type of tool/function only.

            Format your response as a JSON array like this:
            ```json
            
            "templates": [
                
                "subgoal_index": 0,
                "tool": "Function definition or ToolName",
                "operation": "One of Tool",
                "template_type": "API",
                "template": "/read?emp_id=<emp_id>&product_id=<product_id>",
                "placeholders": 
                    "emp_id": "Employee ID,
                    "product_id": "Product ID,
                ,
                "expected_output": "Dictionary of all the keys in return type of tool/function called with corresponding values",
                
            ]
            

        ```
        """
        
        response = llm.gpt(prompt)
        return response

class TaskGeneration:
    """Generate final CRUD task"""
    
    def generate_task(self, data_chain: List[str], primary_goal: str, 
                     subgoals: Dict, tool_dependencies: str, templates: str,
                     datasource_desc,datasource_context,  persona: str, llm) -> str:
        """
        Generate the final CRUD task
        
        Args:
            data_chain: List of data chains
            primary_goal: Main CRUD goal
            subgoals: Subgoals
            tool_dependencies: Tool dependencies
            templates: Templates for operations
            context: Context data
            persona: User persona
            llm: Language model
            
        Returns:
            Final task description in JSON format
        """
        prompt = f"""
            You are an enterprise data systems expert tasked with defining an end-to-end CRUD task specification using API-based tools. The final result of Primary goal should be Ground Truth.

            Based on the following inputs:

            Primary goal:
            {primary_goal}

            User persona:
            {persona}

            Data chain sources involved:
            {data_chain}

            Subgoals:
            {json.dumps(subgoals, indent=2)}

            Tools:
            {json.dumps(tool_dependencies, indent=2)}

            API call templates:
            {json.dumps(templates, indent=2)}

            Database description:
            {json.dumps(datasource_desc, indent=2)}

            Ground Truth:
            {json.dumps(datasource_context, indent=2)}

            Your task is to create a complete CRUD task specification that includes:
            - A detailed description explaining the full goal that is posed as a question/task.
            - A full API link for that corresponding task (like Postman CRUD API call) like:
                - if task is to Create the Api link="/create?emp_id="emp1234"&.....(include all the fields and their values mentioned in Ground Truth)
                - stick only to the tool names mentioned in Tools.
                - mention all the parameters mention in Ground Truth while creating the link and their values, don't leave any argument as placeholder(in <> or [])
            - The operation type (Create, Read, Update, or Delete)
            - Don't create synthetic data_sources, stick to only the data chain datesource
            - A full list of subgoals:
                For each subgoal, add a subgoal to extract entries from the API call

            
            Format the output as follows:
            ```json
            "task": "task",
            "api_call": "Api link for corresponding task"
            "operation_type": "One of: Create, Read, Update, Delete",
            "data_sources": ["source"],
            "subgoals": [
                
                "subgoal": "First step description",
                "operation": "One of the tool (if extraction or parsing use LLM tool)",
                "expected_outcome": "Dictionary of all the keys in return type of tool/function called with corresponding values",
                "data source": "Relevant data source for this step",
                "thinking_trace": "Detailed reasoning about how to accomplish this subgoal using the tools/functions and data sources"
                ,....
            ],
            "ground_truth": Ground Truth...,

        ```
        """
        
        response = llm.gpt(prompt)
        return response