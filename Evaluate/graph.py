"""
ReAct Graph with LOCAL MODEL Support + vLLM SERVER Support + ROBUST Tool Parsing
✅ NEW: Support for vLLM server via OpenAI API
✅ Maintains all existing functionality
"""
import json
import asyncio
import ast
from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from langchain_openai import OpenAI as LangChainOpenAI
from langchain_openai import AzureChatOpenAI
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from langgraph.graph import StateGraph, add_messages, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from langchain.tools import BaseTool
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.agents import AgentAction, AgentFinish
from pydantic import BaseModel, ValidationError
# from langchain_core.messages import RemoveMessage
from langchain_google_genai import ChatGoogleGenerativeAI

import boto3
from langchain_aws import ChatBedrock
import time
from typing import List, Annotated, Literal, Dict, Any, Optional
import os
import json
import re
import uuid
from datetime import datetime
from dotenv import load_dotenv
import torch
import httpx
from openai import OpenAI
from pathlib import Path

load_dotenv()

# Configuration
LOCAL_MODEL_PATH = os.getenv("LOCAL_MODEL_PATH", "")
TOOL_EXAMPLES_PATH = os.getenv("TOOL_EXAMPLES_PATH", "tool_examples.json")
# NEW: vLLM Server Configuration
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "")

# Takane Configuration
TAKANE_BASE_URL = os.getenv("TAKANE_BASE_URL", "https://api-management.kozuchi.css.fujitsu.com/takane-3/v1")
TAKANE_API_KEY = os.getenv("TAKANE_API_KEY", "")
TAKANE_MODEL = os.getenv("TAKANE_MODEL", "takane-v3-koba-20260630")

# Modes: "local" or "vllm"
MODEL_MODE = os.getenv("MODEL_MODE", "vllm")  # azure/vllm/local/bedrock/gemini/takane
DEBUG_MODE = os.getenv("DEBUG_MODE", "True").lower() == "true"

TOOL_CALLING_PROMPT_PATH = Path(__file__).resolve().parent / "tool_calling_prompt.txt"

class TrajectoryStep(BaseModel):
    step_number: int
    step_type: Literal["thought", "action", "observation", "clarification"]
    content: str
    timestamp: str
    tool_used: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[str] = None

class AgentState(BaseModel):
    messages: Annotated[List, add_messages]
    trajectory: List[TrajectoryStep] = []
    current_step: int = 0
    max_steps: int = 25
    task_completed: bool = False
    current_query: str = ""
    final_answer: str = ""
    needs_clarification: bool = False
    clarification_question: str = ""
    enable_clarification: bool = True
    subtasks_identified: List[str] = []
    subtasks_completed: List[str] = []
    pending_subtasks: List[str] = []

def extract_tool_calls_from_trajectory(trajectory: List[TrajectoryStep]) -> List[Dict[str, Any]]:
    """Extract the ordered list of {tool_name, tool_arguments} actually executed by the agent."""
    calls = []
    for step in trajectory:
        if step.step_type == "action" and step.tool_used:
            calls.append({
                "tool_name": step.tool_used,
                "tool_arguments": step.tool_input or {}
            })
    return calls


def save_trajectory_to_file(trajectory: List[TrajectoryStep], query: str, final_answer: str = ""):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"trajectory_{timestamp}.json"
    trajectory_data = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "final_answer": final_answer,
        "total_steps": len(trajectory),
        "trajectory": [step.dict() for step in trajectory]
    }
    os.makedirs("trajectories", exist_ok=True)
    filepath = os.path.join("trajectories", filename)
    with open(filepath, "w") as f:
        json.dump(trajectory_data, f, indent=2)
    print(f"📁 Trajectory saved to: {filepath}")
    return filepath
def load_bedrock_model():
        AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
        AWS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
        AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
        session = boto3.Session(region_name=AWS_REGION)
        bedrock_client = session.client(
            "bedrock-runtime",
            endpoint_url=f"https://bedrock-runtime.{AWS_REGION}.amazonaws.com"
        )
        llm = ChatBedrock(
   
            model_id = "",
            client=bedrock_client,
            model_kwargs={
                "temperature": 0,
                "max_tokens": 8192   #change to 10000 for claude 4.5
            },
            beta_use_converse_api=True,
            disable_streaming=False
        )
        llm = llm.bind()
        # llm_with_tools = llm.bind_tools(tools) if tools else llm
        return llm
def load_local_model(model_path: str, device: str = "auto"):
    """Load model locally via HuggingFace"""
    print(f"🔄 Loading local model from: {model_path}")
    num_gpus = torch.cuda.device_count()
    print(f"📊 Available GPUs: {num_gpus}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        local_files_only=True
    )
    
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=512,
        temperature=0.1,
        do_sample=True,
        top_p=0.95,
        return_full_text=False
    )
    
    hf_pipeline = HuggingFacePipeline(pipeline=pipe, 
                                      model_kwargs={"chat_template_kwargs": {"enable_thinking": False}})
    chat_model = ChatHuggingFace(llm=hf_pipeline)
    print(f"✅ Local model loaded successfully")
    return chat_model
def load_gemini_model():
    llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-pro",  # or "gemini-2.0-flash-exp"
            project="genai-gemini-testing",
            location="global",  # or "us-central1"
            temperature=0,
            max_output_tokens=65536,
        )
    llm = llm.bind(
            response_format={"type": "json_object"}
        )
    # llm_with_tools = llm.bind_tools(tools) if tools else llm
    return llm
def load_vllm_model(base_url: str, api_key: str):
    """✅ NEW: Load model via vLLM OpenAI-compatible server"""
    print(f"🔄 Connecting to vLLM server at: {base_url}")
    
    # Test connection and get model name
    try:
        client = OpenAI(base_url=base_url, api_key=api_key)
        models = client.models.list()
        if not models.data:
            raise ValueError("No models available from vLLM server")
        
        model_name = models.data[0].id
        print(f"✅ Connected to vLLM server")
        print(f"📋 Available model: {model_name}")
        
        # Create LangChain-compatible wrapper
        from langchain_openai import ChatOpenAI
        
        chat_model = ChatOpenAI(
            model=model_name,
            openai_api_base=base_url,
            openai_api_key=api_key,
            temperature=0.1,
            max_tokens=8192,
            extra_body={
                "chat_template_kwargs": {"enable_thinking": False}
            }
        )
        
        print(f"✅ vLLM model wrapper created")
        return chat_model, model_name
        
    except Exception as e:
        print(f"❌ Failed to connect to vLLM server: {e}")
        print(f"   Make sure vLLM is running on {base_url}")
        raise
def load_takane_model():
    """Load Takane (Fujitsu) model via its OpenAI-compatible endpoint"""
    if not TAKANE_API_KEY:
        raise ValueError("TAKANE_API_KEY is not set. Add it to your .env file.")

    print(f"🔄 Connecting to Takane at: {TAKANE_BASE_URL}")
    from langchain_openai import ChatOpenAI

    # Takane is a reasoning model behind a corporate gateway - it can take well over a
    # minute per call (hidden <think> tokens included). httpx's default 5s connect/read
    # timeout was silently killing requests mid-generation, which then got retried by
    # BOTH the openai SDK's own retry logic AND the 5x retry loop in think_node/action_node,
    # compounding into very long effective waits. Give it a generous timeout and let only
    # the graph-level retry loop handle retries (max_retries=0 here) to avoid double-retrying.
    takane_timeout = httpx.Timeout(180.0, connect=30.0)

    llm = ChatOpenAI(
        model=TAKANE_MODEL,
        openai_api_base=TAKANE_BASE_URL,
        openai_api_key=TAKANE_API_KEY,
        temperature=0.2,
        max_tokens=8192,
        timeout=takane_timeout,
        max_retries=0,
        default_headers={
            "Authorization": f"Bearer {TAKANE_API_KEY}",
            "Ocp-Apim-Subscription-Key": TAKANE_API_KEY,
        },
        http_client=httpx.Client(verify=False, timeout=takane_timeout),
        http_async_client=httpx.AsyncClient(verify=False, timeout=takane_timeout),
    )
    print(f"✅ Connected to Takane model: {TAKANE_MODEL}")
    return llm


def load_gpt_model():
    api_key = os.getenv("AZURE_API_KEY")
    api_base = os.getenv("AZURE_API_ENDPOINT")
    azure_api_version = os.getenv("AZURE_API_VERSION")
    # ✅ FIX 1: Add timeout and max_tokens to prevent runaway context
    llm = AzureChatOpenAI(
        api_key=api_key,
        azure_endpoint=api_base,
        api_version="2024-02-01",
        temperature=0.1,
    )
    llm = llm.bind(
            response_format={"type": "json_object"}
        )
    # llm_with_tools = llm.bind_tools(tools) if tools else llm
    return llm

def get_tool_schema_description(tool: BaseTool) -> str:
    """Compact tool description: one line per parameter, no decorative padding.

    This is resent as part of the system prompt on every single LLM call (think AND
    action node, every ReAct step), so its token count multiplies directly into total
    latency/cost across a batch - keep it dense, not pretty.
    """
    schema = get_tool_schema_safe(tool)
    lines = [f"### {tool.name}", tool.description.strip()]

    if schema and 'properties' in schema:
        declared_required = set(schema.get('required', []))

        def is_required(name: str, desc: str) -> bool:
            return name in declared_required or desc.startswith("[REQUIRED]")

        param_lines = []
        required_params = {}
        for param_name, param_info in schema['properties'].items():
            param_type = param_info.get('type', 'string')
            raw_desc = param_info.get('description', '')
            req = is_required(param_name, raw_desc)
            desc = raw_desc[len("[REQUIRED] "):] if raw_desc.startswith("[REQUIRED] ") else raw_desc
            default_val = param_info.get('default', None)
            enum_vals = param_info.get('enum', None)

            extra = ""
            if default_val is not None:
                extra += f", default={default_val}"
            if enum_vals:
                extra += f", one of {list(map(str, enum_vals))}"

            tag = "required" if req else "optional"
            param_lines.append(f"  - {param_name} ({param_type}, {tag}{extra}): {desc}")

            if req:
                required_params[param_name] = f"<{param_type}>"

        if param_lines:
            lines.append("Parameters:")
            lines.extend(param_lines)

        if required_params:
            example = {"action": tool.name, "action_input": required_params}
            lines.append(f"Example: {json.dumps(example)}")

    return "\n".join(lines) + "\n"


def get_tool_schema_safe(tool: BaseTool) -> dict:
    """Safely extract tool schema"""
    try:
        if hasattr(tool, 'args_schema') and tool.args_schema:
            if isinstance(tool.args_schema, dict):
                return tool.args_schema
            elif hasattr(tool.args_schema, 'schema'):
                return tool.args_schema.schema()
            elif hasattr(tool.args_schema, 'model_json_schema'):
                return tool.args_schema.model_json_schema()
        return {}
    except Exception as e:
        print(f"Warning: Could not extract schema for {tool.name}: {e}")
        return {}




def validate_tool_input_with_correction(tool_name: str, tool_args: Dict[str, Any], tools: List[BaseTool]) -> Optional[Dict[str, Any]]:
    """Validate with parameter name auto-correction"""
    tool = next((t for t in tools if t.name == tool_name), None)
    print("Tool name", tool_name)
    if not tool:
        print(f"❌ Tool {tool_name} not found")
        return {}, False
    
    # If no schema validation needed, return as-is
    if not hasattr(tool, 'args_schema') or tool.args_schema is None:
        return tool_args, True
    
    # Handle correct description fetch
    
    # Handle dict-based schemas
    if isinstance(tool.args_schema, dict):
        print("🔍 Validating against dict schema with auto-correction")
        schema = tool.args_schema
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        # Parameter aliases for common variations
        param_aliases = {
            'project_id': ['repository_id', 'repo_id'],
            'repository_name': ['repo_name', 'project_name', 'repo', 'name'],
            'name': ['repository_name', 'repo_name', 'project_name'],
            'branch': ['branch_name', 'branch_id', 'ref', 'branch_ref'],
            'message': ['commit_message', 'msg', 'description', 'commit_msg'],
            'content': ['file_content', 'body', 'data', 'text'],
            'path': ['file_path', 'filepath', 'file', 'filename'],
        }
        
        # Build reverse lookup
        alias_to_param = {}
        for param, aliases in param_aliases.items():
            for alias in aliases:
                alias_to_param[alias] = param
        
        # Correct the arguments
        corrected_args = {}
        matched= True
        for provided_key, value in tool_args.items():
            matched = False
            
            # Strategy 1: Exact match
            if provided_key in properties:
                corrected_args[provided_key] = value
                print(f"  ✅ Exact match: {provided_key}")
                matched = True
            
            # Strategy 2: Check if provided_key is an alias
            elif provided_key in alias_to_param and alias_to_param[provided_key] in properties:
                correct_key = alias_to_param[provided_key]
                corrected_args[correct_key] = value
                print(f"  🔄 Corrected {provided_key} → {correct_key}")
                matched = True
            
            # Strategy 3: Fuzzy match
            if not matched:
                for expected_param in properties.keys():
                    if (provided_key.lower() in expected_param.lower() or 
                        expected_param.lower() in provided_key.lower()):
                        corrected_args[expected_param] = value
                        print(f"  🔍 Fuzzy match: {provided_key} → {expected_param}")
                        matched = True
                        break
            
            # If still no match, keep as-is
            if not matched:
                corrected_args[provided_key] = value
                print(f"  ⚠️ No match found for: {provided_key}, keeping as-is")
        
        # Check for missing required fields
        missing_fields = [field for field in required if field not in corrected_args]
        if missing_fields:
            print(f"  ❌ Missing required: {missing_fields}")
            
            return f"Missing required: {missing_fields}", False
        
        print("  ✅ Validation passed")
        print(f"  📦 Final args: {json.dumps(corrected_args, indent=6)}")
        
        return corrected_args, matched
    
    # Handle Pydantic schemas
    try:
        schema_name = getattr(tool.args_schema, '__name__', 'UnknownSchema')
        print(f"🔍 Validating against {schema_name}")
        
        if hasattr(tool.args_schema, 'model_validate'):
            validated = tool.args_schema.model_validate(tool_args)
            validated_dict = validated.model_dump()
        elif hasattr(tool.args_schema, 'parse_obj'):
            validated = tool.args_schema.parse_obj(tool_args)
            validated_dict = validated.dict()
        else:
            return tool_args, True
        
        print("  ✅ Validation passed")
        return validated_dict, True
        
    except ValidationError as e:
        print(f"  ❌ VALIDATION FAILED:")
        for error in e.errors():
            field = "->".join(str(loc) for loc in error['loc'])
            print(f"    -  {field}: {error['msg']}")
        return {}, False
    except Exception as e:
        print(f"  ⚠️ Error: {e}")
        return {}, False
def load_tool_calling_prompt_template() -> str:
    with open(TOOL_CALLING_PROMPT_PATH, "r") as f:
        return f.read()


def get_base_prompt(tools: List[BaseTool]) -> str:
    """Build the merged think+action system prompt from tool_calling_prompt.txt.

    Substitution is a plain string.replace() rather than str.format() because the
    template itself contains other literal `{...}` JSON braces (the <tool> example).
    """
    tool_descriptions = "".join([get_tool_schema_description(tool) for tool in tools]) if tools else "No tools available."
    template = load_tool_calling_prompt_template()
    return template.replace("{tools}", tool_descriptions)
def build_react_agent_graph(tools: List[BaseTool], enable_clarification: bool = True,
                           model_mode: Optional[str] = None):
    """
    ✅ UPDATED: Support both local and vLLM server modes
    
    Args:
        tools: List of available tools
        enable_clarification: Whether to enable clarification mode
        model_mode: "local" or "vllm" (defaults to MODEL_MODE env var)
    """
    
    mode = MODEL_MODE
    print("CURRENT MODE of EVALUATION", mode)
    if tools:
        print(f"\n📚 Loading {len(tools)} tools...")

    # Merged think+action prompt from tool_calling_prompt.txt (see get_base_prompt).
    # `enable_clarification` is accepted for backward API compatibility but the merged
    # prompt template has no clarification mode - callers should treat this as unused.
    system_prompt = get_base_prompt(tools)

    # ✅ Load model based on mode
    if mode == "vllm":
        llm, vllm_model_name = load_vllm_model(VLLM_BASE_URL, VLLM_API_KEY)
        print(f"🤖 Using vLLM SERVER mode: {vllm_model_name}")
        llm_with_stop = llm.bind(stop=["<tool_result>"])  # stop before the model can hallucinate a fake tool result
        use_local_parser = True  # vLLM uses same parsing as local
    elif mode == "local":
        llm = load_local_model(LOCAL_MODEL_PATH)
        print(f"🤖 Using LOCAL model mode")
        llm_with_stop = llm.bind(stop=["<tool_result>"])  # stop before the model can hallucinate a fake tool result
        use_local_parser = True
    elif mode == "azure":
        llm = load_gpt_model()
        print(f"🤖 Using GPT model mode")
        llm_with_stop = llm.bind(stop=["<tool_result>"])  # stop before the model can hallucinate a fake tool result
        use_local_parser = False
    elif mode == "bedrock":
        llm = load_bedrock_model()
        print(f"🤖 Using BEDROCK model mode")
        llm_with_stop = llm.bind(stop=["<tool_result>"])  # stop before the model can hallucinate a fake tool result
        use_local_parser = False
    elif mode == "gemini":
        llm = load_gemini_model()
        print(f"🤖 Using GEMINI model mode")
        llm_with_stop = llm.bind(stop=["<tool_result>"])  # stop before the model can hallucinate a fake tool result
        use_local_parser = False
    elif mode == "takane":
        llm = load_takane_model()
        print(f"🤖 Using TAKANE model mode")
        llm_with_stop = llm.bind(stop=["<tool_result>"])  # stop before the model can hallucinate a fake tool result
        use_local_parser = False
    else:
        raise ValueError(f"Unknown model mode: {mode}. Use one of 'local', 'vllm', 'azure', 'bedrock', 'gemini', 'takane'")
    
    def parse_thinking(text: str):
        if "<think>" in text and "</think>" in text:
            start = text.find("<think>")
            end = text.find("</think>") + len("</think>")
            thinking = text[start:end]
            remainder = text[end:].strip()
            return thinking, remainder
        return "", text

   
    def parse_json(json_str):
        """Enhanced JSON parser with robust error handling for LLM outputs"""
        # Remove code block markers
        if json_str.startswith("```"):
            json_str = json_str[len("```json"):].strip() if json_str.startswith("```json") else json_str[3:].strip()
        if json_str.endswith("```"):
            json_str = json_str[:-3].strip()
        if json_str.startswith("<tool_call>"):
            json_str = json_str[len("<tool_call>"):].strip()
        if json_str.endswith("</tool_call>"):
            json_str = json_str[:-len("</tool_call>")].strip()
        
        try:
            # Strategy 1: Standard JSON parsing
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # Strategy 2: Fix unescaped control characters
            try:
                fixed_str = json_str.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                return json.loads(fixed_str)
            except json.JSONDecodeError:
                # Strategy 3: Handle truncated strings
                try:
                    fixed_str = json_str.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                    
                    # Fix truncation
                    if fixed_str.rstrip().endswith('\\'):
                        fixed_str = fixed_str.rstrip('\\') + '"}'
                    
                    # Fix missing closing braces
                    open_braces = fixed_str.count('{')
                    close_braces = fixed_str.count('}')
                    if open_braces > close_braces:
                        fixed_str += '}' * (open_braces - close_braces)
                    
                    return json.loads(fixed_str)
                except json.JSONDecodeError:
                    # Strategy 4: Try Python dict syntax
                    try:
                        data = ast.literal_eval(json_str)
                        return data
                    except (ValueError, SyntaxError):
                        # Strategy 5: Last resort
                        try:
                            json_str_fixed = json_str.replace("'", '"')
                            return json.loads(json_str_fixed)
                        except json.JSONDecodeError as final_error:
                            print(f"Parsing failed for string {json_str[:200]}... with error: {final_error}")
                            return {"action": "Tool Call failed", "action_input": {}}

    def parse_agent_action(text: str):
        """Parse a merged think+action response per tool_calling_prompt.txt's
        <reasoning>...</reasoning> + either <tool>{...}</tool> or <answer>...</answer> format.

        Returns (reasoning, kind, payload):
          kind == "tool"   -> payload = {"tool": name, "input": args}
          kind == "answer" -> payload = the answer text
          kind is None      -> neither tag was found; payload is the raw text as a fallback
        """
        reasoning_match = re.search(r"<reasoning>(.*?)</reasoning>", text, re.DOTALL)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

        tool_match = re.search(r"<tool>(.*?)</tool>", text, re.DOTALL)
        if tool_match:
            tool_json = parse_json(tool_match.group(1).strip())
            name = tool_json.get("name") or tool_json.get("action", "")
            args = tool_json.get("args")
            if args is None:
                args = tool_json.get("action_input", {})
            return reasoning, "tool", {"tool": name, "input": args}

        answer_match = re.search(r"<answer>(.*?)</answer>", text, re.DOTALL)
        if answer_match:
            return reasoning, "answer", answer_match.group(1).strip()

        return reasoning, None, text

    def filter_messages_for_local_model(messages: List, current_query: str = "", include_system_prompt: bool = True) -> List:
        """
        Build clean conversation history for local models:
        1. System prompt (once, if include_system_prompt=True)
        2. ALL User queries (not just the first one)
        3. Intermediate steps (thought -> action -> observation cycles)
        """
        filtered = []
        system_added = False
        
        for msg in messages:
            # Add System message only once
            if isinstance(msg, SystemMessage):
                if not system_added and include_system_prompt:
                    filtered.append(msg)
                    system_added = True
                continue
            
            # ✅ FIX: Add ALL user messages (not just the first one)
            if isinstance(msg, HumanMessage):
                # Skip only the intermediate prompts like "THINK NODE:" and "ACTION NODE:"
                if "THINK NODE:" in msg.content or "ACTION NODE:" in msg.content:
                    continue
                else:
                    # Add all genuine user messages
                    filtered.append(msg)
            
            elif isinstance(msg, AIMessage):
                # msg.content is already <reasoning>...</reasoning> (+ <answer>...</answer>
                # for finished turns) from agent_node - only tool-call turns need the
                # matching <tool>{...}</tool> tag appended, since that part lives in
                # msg.tool_calls rather than msg.content.
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    tool_name = msg.tool_calls[0].get('name', 'unknown')
                    tool_args = msg.tool_calls[0].get('args', {})
                    tool_tag = json.dumps({"name": tool_name, "args": tool_args})
                    formatted_msg = AIMessage(
                        content=f"{msg.content}<tool>{tool_tag}</tool>",
                        tool_calls=msg.tool_calls
                    )
                    filtered.append(formatted_msg)
                elif msg.content:
                    filtered.append(msg)

            elif isinstance(msg, ToolMessage):
                filtered.append(
                    HumanMessage(content=f"<tool_result>{msg.content}</tool_result>")
                )
        
        # Add system prompt at the beginning if not already added and requested
        if include_system_prompt and not system_added:
            filtered.insert(0, SystemMessage(content=system_prompt))
        
        return filtered



    def build_conversation_summary(state: AgentState) -> str:
        """Build a concise summary of conversation progress"""
        summary_parts = []
        
        for step in state.trajectory:
            if step.step_type == "thought":
                try:
                    thought_data = json.loads(step.content)
                    summary_parts.append(f"💭 Thought: {thought_data.get('thought', step.content)}")
                except:
                    summary_parts.append(f"💭 Thought: {step.content}")
            
            elif step.step_type == "action":
                if step.tool_used:
                    summary_parts.append(f"⚡ Action: {step.tool_used}({json.dumps(step.tool_input)})")
                else:
                    summary_parts.append(f"⚡ Action: {step.content}")
            
            elif step.step_type == "observation":
                summary_parts.append(f"👁️ Observation: {step.content}")
        
        return "\n".join(summary_parts[-5:])  # Last 5 steps only


    def agent_node(state: AgentState) -> AgentState:
        """Merged think+action step: one LLM call produces <reasoning> plus either a
        <tool> call or an <answer>, instead of the old two-call think_node/action_node
        pair. Halves the number of LLM round-trips (and repeated system-prompt tokens)
        per ReAct step."""
        step_num = len([s for s in state.trajectory if s.step_type == "action"]) + 1
        if DEBUG_MODE:
            print(f"\n{'='*80}")
            print(f"🤖 AGENT NODE - Step {step_num}/{state.max_steps}")
            print(f"{'='*80}")

        conversation_summary = build_conversation_summary(state)

        agent_prompt = f"""Current Query: {state.current_query}
Conversation Summary:
{conversation_summary}

Continue the task: produce exactly one <reasoning> block followed by either one <tool> call
or one <answer>, per the system instructions."""

        # ✅ CRITICAL FIX: Handle messages differently for GPT vs Local
        if use_local_parser:
            # Local/vLLM mode: filter and convert ToolMessages
            filtered_messages = filter_messages_for_local_model(state.messages, state.current_query)
            messages = filtered_messages + [HumanMessage(content=agent_prompt)]
        else:
            # ✅ GPT mode: Keep ALL messages intact for OpenAI API
            messages = state.messages + [HumanMessage(content=agent_prompt)]
        if DEBUG_MODE:
            print(f"📊 Message count: {len(messages)}")

        response = None
        steps = 0
        while(steps < 5):
            steps += 1
            try:
                response = llm_with_stop.invoke(messages)
                break
            except Exception as e:
                time.sleep(15 * steps)
                print(f"Retrying due to error: {e}")
        if response is None:
            response = AIMessage(content="<reasoning>Unable to reach the model.</reasoning><answer>Error: model unreachable.</answer>")

        _model_thinking, remainder = parse_thinking(response.content)
        reasoning, kind, payload = parse_agent_action(remainder)

        if DEBUG_MODE:
            print(f"📝 Reasoning: {reasoning}")
            print(f"🔀 Parsed kind: {kind}")

        thought_step = TrajectoryStep(
            step_number=len(state.trajectory),
            step_type="thought",
            content=reasoning,
            timestamp=datetime.now().isoformat()
        )

        task_completed = False
        final_answer = ""
        ai_message = None
        tool_calls_detected = False
        validated_tool_call = None
        action_content = remainder

        if kind == "answer":
            task_completed = True
            final_answer = payload
            ai_message = AIMessage(content=f"<reasoning>{reasoning}</reasoning><answer>{payload}</answer>")
            action_content = str(final_answer)

        elif kind == "tool":
            tool_name = payload["tool"]
            tool_input = payload["input"]

            validated_args, validation_match = validate_tool_input_with_correction(tool_name, tool_input, tools)
            if validation_match:
                tool_calls_detected = True
                validated_tool_call = {
                    'name': tool_name,
                    'args': validated_args,
                    'id': f"call_{uuid.uuid4().hex[:8]}",
                    'type': 'tool_call'
                }
                ai_message = AIMessage(
                    content=f"<reasoning>{reasoning}</reasoning>",
                    tool_calls=[validated_tool_call]
                )
                print(f"\n🔧 Tool Call Created: {tool_name}")
                print(f"📥 Arguments: {validated_args}")
            else:
                # Missing required args - surface the validator's message and loop back
                # to the agent (same as the old code's behaviour on validation failure).
                ai_message = AIMessage(content=f"<reasoning>{reasoning}</reasoning>{validated_args}")
                action_content = str(validated_args)

        if ai_message is None:
            # Neither <tool> nor <answer> could be parsed - keep the raw text in context
            # and let routing send us back to the agent to retry, rather than guessing.
            ai_message = AIMessage(content=response.content)

        if tool_calls_detected and validated_tool_call:
            action_step = TrajectoryStep(
                step_number=len(state.trajectory) + 1,
                step_type="action",
                content=f"Using {validated_tool_call['name']}: {validated_tool_call['args']}",
                timestamp=datetime.now().isoformat(),
                tool_used=validated_tool_call['name'],
                tool_input=validated_tool_call['args']
            )
        else:
            action_step = TrajectoryStep(
                step_number=len(state.trajectory) + 1,
                step_type="action",
                content=action_content,
                timestamp=datetime.now().isoformat()
            )

        return AgentState(
            messages=state.messages + [ai_message],
            trajectory=state.trajectory + [thought_step, action_step],
            current_step=state.current_step,
            max_steps=state.max_steps,
            task_completed=task_completed,
            current_query=state.current_query,
            final_answer=str(final_answer),
            needs_clarification=False,
            clarification_question="",
            enable_clarification=state.enable_clarification,
            subtasks_identified=state.subtasks_identified,
            subtasks_completed=state.subtasks_completed,
            pending_subtasks=state.pending_subtasks
        )



    def observe_node(state: AgentState) -> AgentState:
        print("\n" + "="*80)
        print("👁️ OBSERVE NODE")
        print("="*80)
        
        if not state.messages:
            return state
        
        last_message = state.messages[-1]
        new_pending = state.pending_subtasks.copy()
        new_completed = state.subtasks_completed.copy()
        
        # ✅ Enhanced tool output display
        if isinstance(last_message, ToolMessage):
            print(f"\n{'='*80}")
            print(f"🔧 TOOL EXECUTION COMPLETE")
            print(f"{'='*80}")
            print(f"📛 Tool Name: {last_message.name}")
            print(f"🆔 Tool Call ID: {last_message.tool_call_id}")
            print(f"✅ Status: {getattr(last_message, 'status', 'success')}")
            print(f"\n📤 TOOL OUTPUT:")
            print(f"{'-'*80}")
            print(f"{last_message.content}")
            print(f"{'-'*80}\n")
            
            # Get the corresponding tool call from previous AIMessage
            tool_input = None
            for msg in reversed(state.messages[:-1]):
                if isinstance(msg, AIMessage) and hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tc in msg.tool_calls:
                        if tc.get('id') == last_message.tool_call_id:
                            tool_input = tc.get('args', {})
                            break
                    if tool_input is not None:
                        break
            print("Tools Name: ", last_message.name)
            if tool_input:
                print(f"📥 Tool Input Used:")
                print(f"{json.dumps(tool_input, indent=2)}")
                print(f"{'='*80}\n")
            
            # Store in trajectory
            observation_step = TrajectoryStep(
                step_number=len(state.trajectory) + 1,
                step_type="observation",
                content=f"Tool {last_message.name} returned: {last_message.content}",
                timestamp=datetime.now().isoformat(),
                tool_used=last_message.name,
                tool_output=last_message.content
            )
            
            return AgentState(
                messages=state.messages,
                trajectory=state.trajectory + [observation_step],
                current_step=state.current_step + 1,
                max_steps=state.max_steps,
                task_completed=state.task_completed,
                current_query=state.current_query,
                final_answer=state.final_answer,
                needs_clarification=state.needs_clarification,
                clarification_question=state.clarification_question,
                enable_clarification=state.enable_clarification,
                subtasks_identified=state.subtasks_identified,
                subtasks_completed=new_completed,
                pending_subtasks=new_pending
            )
        
        return AgentState(
            messages=state.messages,
            trajectory=state.trajectory,
            current_step=state.current_step,
            max_steps=state.max_steps,
            task_completed=state.task_completed,
            current_query=state.current_query,
            final_answer=state.final_answer,
            needs_clarification=state.needs_clarification,
            clarification_question=state.clarification_question,
            enable_clarification=state.enable_clarification,
            subtasks_identified=state.subtasks_identified,
            subtasks_completed=new_completed,
            pending_subtasks=new_pending
        )

    
    def final_node(state: AgentState) -> AgentState:
        # Not writing a per-task trajectory_*.json here: client.py already persists every
        # run's full trajectory (incrementally, with task/eval context) into
        # trajectories/eval_results_<batch_id>.json[l] - a duplicate side-write here just
        # littered the directory with hundreds of redundant, context-free files.
        print(f"\n🏁 FINAL NODE")

        # from langgraph.graph.message import REMOVE_ALL_MESSAGES
        # messages = state.messages
        # if(len(state.messages)>30):
        #     messages = [RemoveMessage(id=REMOVE_ALL_MESSAGES)] 
        # Clear all messages
        return AgentState(
            messages=state.messages,
            trajectory=state.trajectory,
            current_step=state.current_step,
            max_steps=state.max_steps,
            task_completed=True,
            current_query=state.current_query,
            final_answer=state.final_answer,
            needs_clarification=False,
            clarification_question="",
            enable_clarification=state.enable_clarification,
            subtasks_identified=state.subtasks_identified,
            subtasks_completed=state.subtasks_completed,
            pending_subtasks=[]
        )


    
    def should_continue_from_agent(state: AgentState) -> Literal["tools", "agent", "final"]:
        """Route after the merged agent step."""
        print(f"\n🔀 ROUTING from agent:")
        print(f"  Current step: {state.current_step}/{state.max_steps}")
        print(f"  Task completed: {state.task_completed}")

        if state.task_completed:
            print("  → Going to FINAL (task completed)")
            return "final"

        if state.messages:
            last_msg = state.messages[-1]
            if isinstance(last_msg, AIMessage) and getattr(last_msg, 'tool_calls', None):
                print(f"  ✅ Tool calls detected: {[tc['name'] for tc in last_msg.tool_calls]}")
                print("  → Going to TOOLS")
                return "tools"

        if state.current_step >= state.max_steps:
            print("  → Going to FINAL (max steps)")
            return "final"

        print("  → Going to AGENT (no tool call yet, retry)")
        return "agent"

    def should_continue_from_observe(state: AgentState) -> Literal["agent", "final"]:
        return "final" if (state.current_step >= state.max_steps or state.task_completed) else "agent"

    # Build graph
    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("observe", observe_node)
    builder.add_node("final", final_node)

    if tools:
        builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "agent")

    if tools:
        builder.add_conditional_edges("agent", should_continue_from_agent, {
            "tools": "tools", "agent": "agent", "final": "final"
        })
        builder.add_edge("tools", "observe")
        builder.add_conditional_edges("observe", should_continue_from_observe, {"agent": "agent", "final": "final"})
    else:
        builder.add_conditional_edges("agent", should_continue_from_agent, {
            "agent": "agent", "final": "final"
        })

    builder.add_edge("final", END)

    return builder.compile(checkpointer=MemorySaver())

__all__ = ["build_react_agent_graph", "AgentState", "TrajectoryStep", "save_trajectory_to_file",
           "extract_tool_calls_from_trajectory", "get_tool_schema_description",
           "load_local_model", "load_vllm_model", "load_takane_model"]
