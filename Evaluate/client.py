"""
Batch Task Executor with EnterpriseBench Tools Integration
===========================================================
✅ Uses ToolWrapper from EnterpriseBench instead of MCP
✅ All trajectories saved to single JSON file
✅ Interactive and batch modes supported
"""

import asyncio
import json
import os
import sys
import inspect
from langchain_core.messages import HumanMessage, SystemMessage

from contextlib import AsyncExitStack
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional, Any, Dict, Callable
from langchain_core.messages import HumanMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

# Your graph imports
from graph import build_react_agent_graph, AgentState, get_base_prompt
# from graph_llama import build_react_agent_graph, AgentState, get_base_prompt


DEFAULT_MAX_STEPS = 10
TASKS_FILE = "Task_Generation/tasks.json"
ENTERPRISE_BENCH_PATH = ""  # Adjust to your path


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    PURPLE = '\033[95m'
    END = '\033[0m'


class ToolWrapper(BaseTool):
    """Wrapper class for EnterpriseBench tools - LangChain compatible"""
    
    name: str
    description: str
    invoke_fn: Callable = Field(exclude=True)  # Exclude from pydantic serialization
    args_schema: Optional[Type[BaseModel]] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(
        self,
        name: str,
        description: str,
        invoke_fn: Callable,
        args_schema: Dict[str, Any],
        **kwargs
    ):
        # Convert dict schema to Pydantic model if needed
        if isinstance(args_schema, dict) and args_schema:
            # Create dynamic Pydantic model from dict schema
            pydantic_schema = self._create_pydantic_schema(args_schema)
        else:
            pydantic_schema = None
        
        super().__init__(
            name=name,
            description=description,
            invoke_fn=invoke_fn,
            args_schema=pydantic_schema,
            **kwargs
        )
        self.metadata = {}
    
    def _create_pydantic_schema(self, schema_dict: Dict[str, Any]) -> Type[BaseModel]:
        """Convert dict schema to Pydantic BaseModel"""
        from pydantic import create_model
        
        # Extract properties from schema
        properties = schema_dict.get("properties", {})
        required_fields = schema_dict.get("required", [])
        
        # Build field definitions for create_model
        fields = {}
        for field_name, field_info in properties.items():
            field_type = self._get_python_type(field_info.get("type", "string"))
            field_description = field_info.get("description", "")
            
            # Mark as required or optional
            if field_name in required_fields:
                fields[field_name] = (field_type, Field(..., description=field_description))
            else:
                default = field_info.get("default", None)
                fields[field_name] = (field_type, Field(default, description=field_description))
        
        # Create dynamic model
        if fields:
            return create_model(f"{self.name}Schema", **fields)
        else:
            return None
    
    def _get_python_type(self, json_type: str) -> type:
        """Map JSON schema types to Python types"""
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        return type_mapping.get(json_type, str)
    
    def _run(self, **kwargs) -> str:
        """Execute the tool - required by BaseTool"""
        try:
            return self.invoke_fn(**kwargs)
        except Exception as e:
            return f"Error executing {self.name}: {str(e)}"
    
    async def _arun(self, **kwargs) -> str:
        """Async execution - required by BaseTool"""
        # For now, just call sync version
        return self._run(**kwargs)
    
    def __call__(self, **kwargs):
        """Make the tool callable - maintains your original interface"""
        return self._run(**kwargs)


class EnterpriseBenchConnector:
    """Connector for EnterpriseBench tools"""
    
    def __init__(self, base_path: str = ENTERPRISE_BENCH_PATH):
        self.base_path = Path(base_path)
        self.tools_instance = None
        self.tools: List[ToolWrapper] = []
        self.tool_info = []  # You should populate this with your tool metadata
    
    def connect(self) -> bool:
        """Initialize EnterpriseBench Tools class"""
        try:
            original_cwd = os.getcwd()
            
            try:
                # os.chdir(str(self.base_path))
                
                # Import Tools class
                from environment.EnterpriseBench.tools import Tools  # Adjusted import
                
                # Instantiate Tools
                self.tools_instance = Tools()
                
                print(f"✅ Connected to EnterpriseBench")
                print(f"   • Tools class instantiated")
                
                return True
                
            finally:
                os.chdir(original_cwd)
            
        except ImportError as e:
            print(f"❌ Failed to import EnterpriseBench Tools: {e}")
            print(f"   Make sure tools.py exists in {self.base_path}")
            import traceback
            traceback.print_exc()
            return False
            
        except Exception as e:
            print(f"❌ Failed to connect to EnterpriseBench: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_tools(self) -> List[ToolWrapper]:
        """Load all tool methods from Tools class"""
        if not self.tools_instance:
            raise RuntimeError("Must call connect() first!")
        
        try:
            print(f"\n🔧 Loading EnterpriseBench tools...")
            
            # Get all methods from Tools instance
            tool_methods = self._discover_tool_methods()
            
            # Convert each method to a ToolWrapper
            for method_name, method in tool_methods.items():
                tool = self._wrap_tool_method(method_name, method)
                if tool:
                    self.tools.append(tool)
                    print(f"   • Loaded: {method_name}")
            
            print(f"✅ Loaded {len(self.tools)} EnterpriseBench tools")
            return self.tools
            
        except Exception as e:
            print(f"❌ Failed to load EnterpriseBench tools: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _discover_tool_methods(self) -> Dict[str, callable]:
        """
        Discover all tool methods from Tools class
        Excludes internal methods and helpers
        """
        tool_methods = {}
        
        # Get all methods from Tools instance
        for name, method in inspect.getmembers(self.tools_instance, predicate=inspect.ismethod):
            # Skip private/internal methods
            if name.startswith('_'):
                continue
            
            # Skip utility methods
            if name in ['get_tool_context', 'load_json', 'save_json', 'llm']:
                continue
            
            # This is a tool method
            tool_methods[name] = method
        
        return tool_methods
    
    def _wrap_tool_method(self, method_name: str, method: callable) -> Optional[ToolWrapper]:
        """
        Wrap a Tools method into a ToolWrapper
        """
        try:
            # Extract docstring as description
            tool_instance = next((tool for tool in self.tool_info if method_name == tool["name"]), None)
            
            if tool_instance:
                description = tool_instance["description"].strip()
                args_schema = tool_instance.get("arguments", {})
            else:
                # Fallback to docstring if tool_info not available
                description = method.__doc__ or f"EnterpriseBench tool: {method_name}"
                description = description.strip()
                args_schema = {}
            
            # Create executor that calls the tool method
            def executor(**kwargs) -> str:
                """Execute EnterpriseBench tool"""
                try:
                    # The Tools methods expect an 'arguments' dict
                    result = method(arguments=kwargs)
                    
                    # Convert result to string
                    if isinstance(result, list):
                        if len(result) == 0:
                            return "No results found"
                        return str(result)
                    elif isinstance(result, dict):
                        return str(result)
                    else:
                        return str(result)
                        
                except Exception as e:
                    return f"Error: {str(e)}"
            
            # Create ToolWrapper
            tool = ToolWrapper(
                name=method_name,
                description=description,
                invoke_fn=executor,
                args_schema=args_schema
            )
            
            # Add metadata
            tool.metadata = {
                "env": "enterprise_bench",
                "original_name": method_name,
                "domain": self._classify_tool_domain(method_name)
            }
            
            return tool
            
        except Exception as e:
            print(f"⚠️  Failed to wrap tool {method_name}: {e}")
            return None
    
    def _classify_tool_domain(self, method_name: str) -> str:
        """Classify tool by domain based on name"""
        name_lower = method_name.lower()
        
        if any(keyword in name_lower for keyword in ['email', 'mail', 'message']):
            return 'email'
        elif any(keyword in name_lower for keyword in ['calendar', 'event', 'meeting', 'schedule']):
            return 'calendar'
        elif any(keyword in name_lower for keyword in ['crm', 'customer', 'contact', 'lead']):
            return 'crm'
        elif any(keyword in name_lower for keyword in ['hr', 'employee', 'payroll']):
            return 'hr'
        else:
            return 'general'


def save_all_trajectories_to_file(all_results: list, batch_id: str):
    """Save all trajectories from batch execution to a single JSON file"""
    os.makedirs("trajectories", exist_ok=True)
    filename = f"batch_trajectories_qwen_3_4B_base.json"
    filepath = os.path.join("trajectories", filename)
    
    formatted_results = []
    for result in all_results:
        task_data = {
            "task_index": result["task_index"],
            "query": result["query"],
            "description": result.get("description", ""),
            "max_steps": result.get("max_steps", DEFAULT_MAX_STEPS),
            "status": result["status"],
            "final_answer": result.get("final_answer", ""),
            "trajectory_length": result.get("trajectory_length", 0),
            "error": result.get("error", None),
            "trajectory": []
        }
        
        if "trajectory" in result and result["trajectory"]:
            for step in result["trajectory"]:
                if hasattr(step, 'dict'):
                    task_data["trajectory"].append(step.dict())
                elif isinstance(step, dict):
                    task_data["trajectory"].append(step)
        
        formatted_results.append(task_data)
    
    batch_data = {
        "batch_id": batch_id,
        "timestamp": datetime.now().isoformat(),
        "default_max_steps": DEFAULT_MAX_STEPS,
        "total_tasks": len(all_results),
        "successful_tasks": sum(1 for r in all_results if r["status"] == "success"),
        "failed_tasks": sum(1 for r in all_results if r["status"] != "success"),
        "tasks": formatted_results
    }
    
    with open(filepath, "w") as f:
        json.dump(batch_data, f, indent=2)
    
    print(f"\n{Colors.GREEN}📁 All trajectories saved to: {filepath}{Colors.END}")
    return filepath


async def run_task_batch(task: dict, graph, config: dict, task_index: int, total_tasks: int, tools:list,  use_persistent_thread: bool = False):
    """Execute a single task and collect trajectory"""
    messages = task.get("messages", [])

    # Option 1: Get the first user message content (most common)
    user_content = next((msg["content"] for msg in messages if msg.get("role") == "user"), None)

    # Assign it to your query variable
    query = user_content if user_content else ""
    # description = task.get("description", "No description")
    max_steps = task.get("max_steps", DEFAULT_MAX_STEPS)
    
    print(f"\n{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}📋 TASK {task_index}/{total_tasks}{Colors.END}")
    print(f"{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.YELLOW}Query: {Colors.END}{query}")
    print(f"{Colors.YELLOW}Max Steps: {Colors.END}{max_steps}")
    print(f"{Colors.CYAN}{'='*80}{Colors.END}")
    
    # Choose config based on mode
    if use_persistent_thread:
        task_config = config
        
        try:
            current_graph_state = graph.get_state(config)
            if current_graph_state and current_graph_state.values.get("messages"):
                existing_messages = current_graph_state.values["messages"]
                print(f"{Colors.PURPLE}📝 Appending to existing conversation ({len(existing_messages)} messages){Colors.END}")
            else:
                existing_messages = []
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Could not retrieve existing state: {e}{Colors.END}")
            existing_messages = []
            
        # ✅ If this is the first message (empty conversation), add system prompt
        if not existing_messages:
            system_prompt_content = get_base_prompt(tools)
            system_prompt_msg = SystemMessage(content=system_prompt_content)
            existing_messages = [system_prompt_msg]
            print(f"{Colors.GREEN}✅ Added system prompt to conversation{Colors.END}")
        
        current_state = AgentState(
            messages=existing_messages + [HumanMessage(content=query)],
            trajectory=[],
            current_step=0,
            max_steps=max_steps,
            task_completed=False,
            current_query=query,
            final_answer="",
            needs_clarification=False,
            clarification_question="",
            enable_clarification=False,
            subtasks_identified=[],
            subtasks_completed=[],
            pending_subtasks=[]
        )
    else:
        task_config = {
            "configurable": {
                "thread_id": f"batch_task_{task_index}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            }
        }
        
        # ✅ Always start with system prompt in batch mode
        system_prompt_content = get_base_prompt(tools)
        system_prompt_msg = SystemMessage(content=system_prompt_content)
        
        current_state = AgentState(
            messages=[system_prompt_msg] + [HumanMessage(content=query)],
            trajectory=[],
            current_step=0,
            max_steps=max_steps,
            task_completed=False,
            current_query=query,
            final_answer="",
            needs_clarification=False,
            clarification_question="",
            enable_clarification=False,
            subtasks_identified=[],
            subtasks_completed=[],
            pending_subtasks=[]
        )
    
    try:
        final_state = None
        async for event in graph.astream(input=current_state, config=task_config):
            for node_name, node_output in event.items():
                final_state = node_output
        
        if final_state:
            final_answer = final_state.final_answer if hasattr(final_state, 'final_answer') else final_state.get('final_answer', '')
            trajectory = final_state.trajectory if hasattr(final_state, 'trajectory') else final_state.get('trajectory', [])
            
            if final_answer:
                print(f"\n{Colors.GREEN}🎯 ANSWER:{Colors.END}")
                print(f"{Colors.GREEN}{final_answer}{Colors.END}")
            else:
                print(f"{Colors.YELLOW}⚠️ No final answer provided{Colors.END}")
            
            if use_persistent_thread:
                updated_state = graph.get_state(task_config)
                if updated_state and updated_state.values.get("messages"):
                    msg_count = len(updated_state.values["messages"])
                    print(f"{Colors.PURPLE}📊 Conversation now has {msg_count} messages{Colors.END}")
            
            print(f"{Colors.GREEN}✅ Task {task_index} completed - {len(trajectory)}/{max_steps} steps used{Colors.END}")
            
            return {
                "task_index": task_index,
                "query": query,
                "max_steps": max_steps,
                "status": "success",
                "final_answer": final_answer,
                "trajectory_length": len(trajectory),
                "trajectory": trajectory
            }
        else:
            print(f"{Colors.RED}❌ FAILED: No output from graph{Colors.END}")
            return {
                "task_index": task_index,
                "query": query,
                "max_steps": max_steps,
                "status": "failed",
                "error": "No output from graph",
                "trajectory": []
            }
    
    except Exception as e:
        print(f"{Colors.RED}❌ ERROR: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return {
            "task_index": task_index,
            "query": query,
            "max_steps": max_steps,
            "status": "error",
            "error": str(e),
            "trajectory": []
        }


async def interactive_mode(graph, config: dict, tools:list, tools_count: int):
    """Interactive terminal mode - ask questions one by one"""
    print(f"\n{Colors.PURPLE}{Colors.BOLD}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║ 💬 INTERACTIVE MODE                                       ║")
    print("║ Type your queries, press Enter to execute                ║")
    print("║ Commands: 'quit' or 'exit' to stop                       ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    print(f"{Colors.CYAN}📊 Available tools: {tools_count}{Colors.END}")
    print(f"{Colors.CYAN}🎯 Max steps per query: {DEFAULT_MAX_STEPS}{Colors.END}\n")
    
    session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    results = []
    task_number = 1
    
    while True:
        try:
            print(f"{Colors.BOLD}{Colors.CYAN}You [{task_number}]: {Colors.END}", end="")
            user_input = input().strip()
            
            if not user_input:
                print(f"{Colors.YELLOW}⚠️ Empty input, please try again{Colors.END}")
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print(f"\n{Colors.YELLOW}👋 Exiting interactive mode...{Colors.END}")
                break
            
            task = {
                "query": user_input,
                "description": f"Interactive query #{task_number}",
                "max_steps": DEFAULT_MAX_STEPS
            }
            
            result = await run_task_batch(task, graph, config, task_number, "∞", tools, use_persistent_thread=True)
            results.append(result)
            task_number += 1
            
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}⚠️ Interrupted by user{Colors.END}")
            break
        except EOFError:
            print(f"\n{Colors.YELLOW}👋 End of input{Colors.END}")
            break
    
    if results:
        print(f"\n{Colors.CYAN}💾 Saving session trajectories...{Colors.END}")
        filepath = save_all_trajectories_to_file(results, session_id)
        
        success_count = sum(1 for r in results if r['status'] == 'success')
        print(f"\n{Colors.GREEN}✅ Queries executed: {len(results)}{Colors.END}")
        print(f"{Colors.GREEN}✅ Successful: {success_count}{Colors.END}")
        print(f"{Colors.GREEN}📁 Saved to: {filepath}{Colors.END}")


async def main():
    """Main batch execution function"""
    # Check for interactive mode
    interactive = False
    if len(sys.argv) > 1 and sys.argv[1] in ['--interactive', '-i']:
        interactive = True
    
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("╔═══════════════════════════════════════════════════════════╗")
    if interactive:
        print("║ 🤖 Interactive Task Executor (EnterpriseBench)           ║")
    else:
        print("║ 🤖 Batch Task Executor (EnterpriseBench)                 ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    print(f"{Colors.CYAN}Configuration:{Colors.END}")
    print(f"  Mode: {Colors.BOLD}{'INTERACTIVE' if interactive else 'BATCH'}{Colors.END}")
    print(f"  Default max_steps: {DEFAULT_MAX_STEPS}")
    if not interactive:
        print(f"  Tasks file: {TASKS_FILE}")
    print(f"  EnterpriseBench path: {ENTERPRISE_BENCH_PATH}")
    
    # Load tasks only for batch mode
    tasks = []
    if not interactive:
        if not os.path.exists(TASKS_FILE):
            print(f"\n{Colors.RED}❌ ERROR: {TASKS_FILE} not found{Colors.END}")
            print(f"{Colors.YELLOW}Creating sample tasks.json...{Colors.END}")
            
            sample_tasks = [
                {"query": "List all employees in the sales department", "description": "HR query"},
                {"query": "Show me today's calendar events", "description": "Calendar query", "max_steps": 20}
            ]
            
            with open(TASKS_FILE, 'w') as f:
                json.dump(sample_tasks, f, indent=2)
            
            print(f"{Colors.GREEN}✅ Created {TASKS_FILE} with {len(sample_tasks)} sample tasks{Colors.END}")
            print(f"{Colors.YELLOW}Edit this file and run again{Colors.END}")
            return
        
        try:
            with open(TASKS_FILE, 'r') as f:
                tasks = json.load(f)
            print(f"\n{Colors.GREEN}✅ Loaded {len(tasks)} tasks from {TASKS_FILE}{Colors.END}")
        except json.JSONDecodeError as e:
            print(f"{Colors.RED}❌ ERROR: Invalid JSON in {TASKS_FILE}: {e}{Colors.END}")
            return
        
        if not tasks:
            print(f"{Colors.YELLOW}⚠️ No tasks found in {TASKS_FILE}{Colors.END}")
            return
    
    # ✅ Connect to EnterpriseBench and load tools
    print(f"\n{Colors.CYAN}🔗 Connecting to EnterpriseBench...{Colors.END}")
    connector = EnterpriseBenchConnector(ENTERPRISE_BENCH_PATH)
    
    if not connector.connect():
        print(f"{Colors.RED}❌ Failed to connect to EnterpriseBench{Colors.END}")
        return
    
    tools = connector.load_tools()
    
    if not tools:
        print(f"{Colors.YELLOW}⚠️ No tools loaded from EnterpriseBench{Colors.END}")
        print(f"{Colors.YELLOW}Proceeding with LLM-only mode...{Colors.END}")
    
    print(f"\n{Colors.GREEN}✅ Building ReAct agent with {len(tools)} EnterpriseBench tools{Colors.END}")
    graph = build_react_agent_graph(tools, enable_clarification=False)
    
    batch_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    graph_config = {"configurable": {"thread_id": f"batch_{batch_id}"}}
    
    if interactive:
        # Run interactive mode
        await interactive_mode(graph, graph_config, tools, len(tools))
    else:
        # Run batch mode
        print(f"\n{Colors.CYAN}{'='*80}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}🚀 STARTING BATCH EXECUTION{Colors.END}")
        print(f"{Colors.CYAN}{'='*80}{Colors.END}")
        
        results = []
        for i, task in enumerate(tasks, 1):
            result = await run_task_batch(task, graph, graph_config, i, len(tasks),tools, use_persistent_thread=False)
            results.append(result)
            filepath = save_all_trajectories_to_file(results, batch_id)
        
        print(f"\n{Colors.CYAN}{'='*80}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}📊 BATCH EXECUTION SUMMARY{Colors.END}")
        print(f"{Colors.CYAN}{'='*80}{Colors.END}")
        
        success_count = sum(1 for r in results if r['status'] == 'success')
        failed_count = len(results) - success_count
        
        print(f"{Colors.GREEN}✅ Successful: {success_count}/{len(results)}{Colors.END}")
        print(f"{Colors.RED}❌ Failed: {failed_count}/{len(results)}{Colors.END}")
        
        for result in results:
            status_color = Colors.GREEN if result['status'] == 'success' else Colors.RED
            status_icon = "✅" if result['status'] == 'success' else "❌"
            print(f"\n{status_color}{status_icon} Task {result['task_index']}: {result['query'][:60]}...{Colors.END}")
            if result['status'] == 'success':
                print(f"   Trajectory steps: {result.get('trajectory_length', 0)}/{result.get('max_steps', DEFAULT_MAX_STEPS)}")
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}📁 Single file output: {filepath}{Colors.END}")


if __name__ == "__main__":
    print("🚀 Starting EnterpriseBench Task Executor...")
    asyncio.run(main())
