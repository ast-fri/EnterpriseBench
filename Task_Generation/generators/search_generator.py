from Task_Generation_sft_batch2_copy.Factories.search import SubgoalGeneration, TemplateGeneration, SubTaskGeneration, TaskGeneration, GoalGeneration, Validation, Improvement
from Task_Generation_sft_batch2_copy.utils.utils import Utils 
from Task_Generation_sft_batch2_copy.Processors.search_processor import SearchProcessor
import json
import logging
from Task_Generation_sft_batch2_copy.utils.tools import Tools
from Task_Generation_sft_batch2_copy.Factories.llm_factory import LLM_factory
from tqdm import tqdm
from langchain_core.output_parsers import JsonOutputParser
import os
import argparse
import re
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmpTaskGenerationPipeline:
    def __init__(self):
        self.processor = SearchProcessor()
        self.persona=None
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
        
    def convert_sets_to_lists(self, obj):
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: self.convert_sets_to_lists(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_sets_to_lists(i) for i in obj]
        else:
            return obj

    def load_config(self, config_file):
        """Load configuration settings from file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            # Validate required keys
            required_keys = ["source_paths"]
            for key in required_keys:
                if key not in config:
                    logger.error(f"Missing required key in config: {key}")
                    raise KeyError(f"Config file must contain {key}")
                    
            return config
        except FileNotFoundError:
            logger.error(f"Config file not found: {config_file}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Error parsing config JSON")
            raise
    
    def generate_task(self, id, config, tools, output_dir, task_domain):
        """Generate tasks for analyzing a support representative - one for each goal template"""
        
        all_tasks = []
        keys = list(config["source_paths"].keys())
        values = list(config["source_paths"].values())
        
        matched_context = self.processor.main(values, keys, task_domain)
        context = {}
        # # print(matched_context)
        for i, m in enumerate(matched_context):
            context[keys[i]] = matched_context[i]
        
        self.persona = self.processor.get_employee_persona(id["emp_id"])       

        if("GitHub" in keys):
            context["GitHub"]["Code"] = ""
            context["GitHub"]["issues"]["patch"] = ""
        # # print(context)
        if("Employee Data" in keys and "Employee Data" not in context):
            id["emp_id"] = context["Employee Data"]["emp_id"]
            self.persona = context["Employee Data"]

        # Pass into your functions
    
        goal_templates = config["goal_templates"]
        
        # Get tools once (assuming they're the same for all goals)
        tools = tools()
        
        # Iterate through each goal template
        # print(id)
        for goal in goal_templates:
            # # print(tool_context)
            goal = f"Employee emp_id {id["emp_id"]}; {goal}"
            goal = GoalGeneration().generate_goal(
                primary_goal=goal,
                context=context,
                llm=self.llm
            )
            goal = goal.content
            # ## Parse Each subgoal
            
            try:
                # goal = self.parse_json(goal)
                print(goal)
            except Exception as e:
                logger.error(f"Failed to parse goal JSON: {e}")
                continue  # skip to next goal
            # Generate subgoals for this goal
            # # print(goal)
            subgoals = SubgoalGeneration().generate_subgoal(
                primary_goal=goal,
                tool_dependencies=tools,
                context=context,
                llm=self.llm,
            )
            
            subgoals_content = subgoals.content
            # ## Parse Each subgoal
            
            try:
                parsed_subgoals = self.parse_json(subgoals_content)
            except Exception as e:
                logger.error(f"Failed to parse subgoals JSON: {e}")
                continue
            # # print(parsed_subgoals)
            templates = []
            subtasks = []
            tasks = []
            tool_context = ""
            if(isinstance(parsed_subgoals, str)):
                continue
            try:
                # print(parsed_subgoals)
                for i in range (len(parsed_subgoals["subgoals"])): 
                    if(i<len(parsed_subgoals["tools"])):
                        tool_context = Tools().get_tool_context([parsed_subgoals["tools"][i]])
                    # # print(len(tool_context))
                    # # print(tool_context)
                    
                        template = TemplateGeneration().generate_template(
                            subgoal=parsed_subgoals["subgoals"][i],
                            tool_context=tool_context,
                            persona=self.persona,
                            llm=self.llm,
                        )
                        template_content = template.content

                        template_parsed = self.parse_json(template_content)
                        template_parsed["tools"] = tool_context
                        templates.append(template_parsed)
                    
                    
                
                        subtask = SubTaskGeneration().generate_subtask(
                            primary_goal=goal,
                            subgoal=parsed_subgoals["subgoals"][i],
                            template=template_parsed,
                            persona=self.persona,
                            llm=self.llm,
                        )
                        subtask_content = subtask.content
                        subtask_parsed = self.parse_json(subtask_content)
                        subtask_parsed["tools"] = tool_context
                        subtasks.append(subtask_parsed)
            except Exception as e:
                # print(f"Failed due to expection: {e}")
                continue
          
            try:
                task_obj = TaskGeneration().generate_task(
                    primary_goal=goal,
                    context=context,
                    subtasks=subtasks,
                    persona=self.persona,
                    llm=self.llm,
                )
                task_content = task_obj.content
                task_parsed = self.parse_json(task_content)
                task = task_parsed["task"]
                # # print(f"Task: {task}")
                tasks.append({
                    "emp_id": id["emp_id"],
                    "task": task,
                    "ground_truth": task_parsed["ground_truth"],
                    "subtasks": subtasks
                })
            except Exception as e:
                logger.error(f"Failed to parse task JSON or generate task: {e}")
                continue
            tasks = self.convert_sets_to_lists(tasks)
            all_tasks.extend(tasks)
            # # print(tasks)
            
            
        return all_tasks
    
    def pipeline(self,id, config_file, tools, output_dir, task_domain):
        """Main pipeline to generate CRM tasks based on type"""
        
        # Load configuration
        config = self.load_config(config_file)
        
        task = self.generate_task(id, config, tools, output_dir, task_domain)
     
        return task
# Example usage
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="CRM Task Generation Pipeline")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    parser.add_argument("--task_domain")
    parser.add_argument("--task_category")
    parser.add_argument("--output", required=True, help="Output file path for generated task")
    args = parser.parse_args()
    utils = Utils(args.task_domain, args.task_category)
    tools = utils.get_tools()
    ids = utils.get_ids()
    all_tasks=[]
    all_context=[]
    all_tool_context = []
    all_metadata=[]
    for index, id in enumerate(tqdm(ids)):
        # Initialize and run the pipeline
        pipeline = EmpTaskGenerationPipeline()
        all_validations = []  # Store all validation results for analysis
        # Generate a task
        
        task= pipeline.pipeline(id, args.config, tools,args.output, args.task_domain)
        output_dir = args.output
        all_tasks.extend(task)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        with open(f"{output_dir}.json", 'w') as f:
            json.dump(all_tasks, f, indent=2)
    logger.info(f"Task successfully generated and saved to {args.output}")