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
    
    def generate_subgoal(self, data_chain, primary_goal, tool_dependencies, context, llm):
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
            data_chain={data_chain}
            primary_goal={primary_goal}
            tool_dependencies={tool_dependencies}
            context={context}

            ## Instructions ##
            Your task is to break down the given primary goal into granular subgoals. Each subgoal must:
            - Don’t assume context is direct input; first subgoal(s) must extract it using tools IF NECESSARY, with arguments derived from the primary_goal (note: some form of ID, e.g., emp_id, product_id, or customer_id, is always given).
            - Stay strictly aligned with the original primary goal.
            - Map to **one** tool from the provided tool_dependencies.
            - Operate on a **single data source** from the data_chain.
            - Optionally use the output from the previous subgoal to enable layered analysis.
            - Avoid redundancy or synthetic-sounding tasks.

            DO NOT include subgoals that are irrelevant or too broad.
            DO NOT combine multiple tools in a single subgoal.

            # Output:
            Return a JSON with a list of precise subgoals required to achieve the primary goal.

            Example format:
            ```json
            "subgoals": [
                "Run `conversation_sentiment_analyzer` on recent customer chats to detect overall sentiment.",
                "Use the sentiment output to identify conversations with strong negative tones post-support.",
                "Call `support_interaction_analyzer` to extract patterns from those conversations involving negative experiences."
            ]
        """
        
        
        response = llm.claude(prompt)
        return response
            



class ToolDependencyGeneration:
    """
    Tool Dependency Generation with self-reflection and validation.

    This class handles the generation of expected tool outputs based on
    context and available tools, with additional output validation.

    Attributes:
        prompt (str): The generated prompt for tool dependency inference.
    """

    def __init__(self):
        """Initialize the Tool Dependency Generation module."""
        self.prompt = ""

    

    def generate_tool_dependencies(self, context, tools, llm):
        """
        Generate expected outputs for tools based on the given context.

        Args:
            context (str): The user context describing what needs to be analyzed.
            tools (list): List of available tools with their descriptions.
            llm: Language model for generating expected outputs.

        Returns:
            dict: Tool outputs with validation results.
        """
        
        # Base prompt for tool dependency inference
        inference_prompt = f"""
            You are a Tool Dependency Inference Agent.

            # Input:
            context={context}
            tools={tools}

            ## Instructions ##
            You are given a natural language *context* describing what the user wants to analyze or understand, along with a list of available tools. Your job is to *map the context to the functionality of the tools*, and describe the expected outputs if each tool were applied to this context.

            DO NOT generate verbose or overly synthetic descriptions.

            Generate the expected output of each tool given in `tools`.

            Instead, for each tool, generate what the output **should look like** (in tabular format, dictionary, or concise key points) when used for the provided context.

            Make sure your response is grounded in the tool descriptions. Do NOT make assumptions beyond the capabilities defined in each tool.

            # Output:
            Return a JSON structure with keys as tool names and values as the expected output structures when each tool is called on the provided context.

            Example format:
            ```json
            
                "github_issue_code_linker": <
                    "linked_code": [
                        
                            "file_path": "django/core/checks/registry.py",
                            "lines_of_interest": [42, 43, 59],
                            "reason": "Function `register` implementation needs validation for tags parameter"
                        ,
                        
                            "file_path": "django/core/checks/registry.py",
                            "lines_of_interest": [53, 54, 55],
                            "reason": "Error handling in `run_checks` method needs to be updated"
                        
                    ]>
                ,
                "code_patch_generator": <
                    "patches": [
                            "file_path": "django/core/checks/registry.py",
                            "patch": "--- a/django/core/checks/registry.py\\n+++ b/django/core/checks/registry.py\\n@@ -29,6 +29,12 @@ def register(self, check=None, *tags, **kwargs):\\n        kwargs.setdefault('deploy', False)\\n\\n+        if not tags:\\n+            raise ValueError('Tags cannot be empty.')\\n+\\n+        for tag in tags:\\n+            if not isinstance(tag, str):\\n+                raise TypeError('Tags must be strings.')\\n+"
                    ]
                >
            
            ```
        """
        
        # Generate initial tool outputs
        initial_outputs = self._parse_llm_response(llm.claude(inference_prompt))
        # print("Initial_Outputs", initial_outputs)
        
        # Initialize validation results
        validated_outputs = {}
        
        # Create a mapping from tool names to tool objects for easy lookup
        tool_map = {tool["name"]: tool for tool in tools}
        
        # Get the clean tool names that we need to validate
        available_tool_names = [tool["name"] for tool in tools]
        
        # Process each key in initial_outputs
        for raw_key, output_value in initial_outputs.items():
            # Clean up the key by removing escape characters and trailing backslashes
            clean_key = raw_key.rstrip('\\')
            
            # Find the matching tool name from our available tools
            matching_tool_name = None
            for tool_name in available_tool_names:
                if tool_name in clean_key:
                    matching_tool_name = tool_name
                    break
            
            if not matching_tool_name:
                continue  # Skip if no matching tool found
                
            # Get the tool object
            tool = tool_map[matching_tool_name]
            
            # Format the expected output structure for comparison
            expected_format = tool.get("output_format", {})
            
            # Parse the output value if it's still a string
            if isinstance(output_value, str):
                try:
                    output_value = self._parse_llm_response(output_value)
                except ValueError:
                    # If parsing fails, try to clean and repair the JSON string
                    output_value = self._clean_json_string(output_value)
                    try:
                        output_value = self._parse_llm_response(output_value)
                    except ValueError:
                        # If still failing, keep as string
                        pass
            
            # Generate reflection prompt for this specific tool
            reflection_prompt = self._generate_reflection_prompt(
                context=context,
                tool=tool,
                generated_output=output_value
            )
            
            # Get validation results
            validation_result = self._parse_llm_response(llm.claude(reflection_prompt))
            
            # Store the validated/corrected output
            if validation_result.get("is_valid", False):
                validated_outputs[matching_tool_name] = {
                    "output": output_value,
                    "validation": validation_result
                }
            else:
                # Use corrected output if available
                validated_outputs[matching_tool_name] = {
                    "output": validation_result.get("corrected_output", output_value),
                    "validation": validation_result
                }
        
        return validated_outputs

    def _clean_json_string(self, json_str):
        """
        Clean and repair common issues with JSON strings in LLM outputs.
        
        Args:
            json_str (str): The JSON string to clean
            
        Returns:
            str: Cleaned JSON string
        """
        import re
        
        # Handle double-escaped backslashes in the string
        json_str = json_str.replace('\\\\', '\\')
        
        # Handle escaped quotes
        json_str = json_str.replace('\\"', '"')
        
        # Remove surrounding curly braces if they exist and are unbalanced
        if json_str.startswith('{') and not json_str.endswith('}'):
            json_str = json_str[1:]
        if not json_str.startswith('{') and json_str.endswith('}'):
            json_str = json_str[:-1]
        
        # Ensure proper JSON structure
        if not (json_str.startswith('{') and json_str.endswith('}')):
            json_str = '{' + json_str + '}'
        
        return json_str

    def _generate_reflection_prompt(self, context, tool, generated_output):
        """
        Generate a prompt for self-reflection on a specific tool's output.
        
        Args:
            context (str): The original user context.
            tool (dict): The tool definition.
            generated_output: The initially generated output for this tool.
            
        Returns:
            str: A prompt for self-reflection.
        """
        return f"""
            You are a Tool Output Validator specializing in code-related tools for software engineering tasks.

            # Input:
            - User Context: {context}
            - Tool Definition: {tool}
            - Generated Output: {generated_output}

            ## Instructions ##
            Carefully analyze whether the generated output for this tool meets these criteria:

            1. Format Correctness: Does the output follow the expected format defined in tool["output_format"]?
            2. Content Relevance: Is the content relevant to the user context and GitHub issue?
            3. Technical Accuracy: For code-related outputs:
               - Are file paths realistic for the repository structure?
               - Is the code syntax valid for the programming language used?
               - Do patches follow correct Git-style unified diff format?
               - Are the code changes logical and address the issue described?
               - Would the patch actually resolve the described problem?
            4. Completeness: Does the output include all necessary information to resolve the GitHub issue?

            # Output:
            Return a JSON structure with your validation results:
            ```json
            
                "is_valid": true/false,
                "issues": [
                    "List any issues found, if any"
                ],
                "corrected_output": "Include a corrected version if needed"
            
            ```
        """

    def _parse_llm_response(self, llm_response):
        """
        Parse JSON from LLM response with extensive error recovery mechanisms.
        Handles code blocks, malformed JSON, multiline strings, and many common JSON errors.
        
        Args:
            llm_response (str): The raw response from the language model
            
        Returns:
            dict: Parsed JSON object
        """
        import re
        import json
        import ast
        
        json_str = llm_response
        
        # Extract JSON from code blocks if present
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', json_str, re.DOTALL)
        if match:
            json_str = match.group(1)
        
        # Replace common substitution patterns
        json_str = json_str.replace("<", "{").replace(">", "}")
        json_str = json_str.strip()
        
        # Try direct parsing first
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Only wrap in {} if clearly needed and not already valid JSON-like
            if not (json_str.startswith('{') or json_str.startswith('[')):
                wrapped_json_str = '{' + json_str + '}'
                try:
                    return json.loads(wrapped_json_str)
                except json.JSONDecodeError:
                    # Continue with original string if wrapping didn't help
                    pass
        
        # Fix common JSON structural issues
        fixes = [
            # Fix 1: Replace unescaped newlines in strings
            (lambda s: re.sub(r'(?<!\\)"([^"]*?)(?:\n)([^"]*?)(?<!\\)"', r'"\1\\n\2"', s)),
            
            # Fix 2: Add missing quotes around keys
            (lambda s: re.sub(r'([{,]\s*)([a-zA-Z0-9_]+)(\s*:)', r'\1"\2"\3', s)),
            
            # Fix 3: Convert single quotes to double quotes (carefully)
            (lambda s: re.sub(r"(?<!\\)'([^']*?)(?<!\\)'", r'"\1"', s)),
            
            # Fix 4: Fix trailing commas in objects/arrays
            (lambda s: re.sub(r',(\s*[}\]])', r'\1', s)),
            
            # Fix 5: Add missing commas between elements
            (lambda s: re.sub(r'(["}\]]\s*)(["{\[])', r'\1,\2', s)),
            
            # Fix 6: Handle unquoted field values
            (lambda s: re.sub(r':\s*([\w.+-]+)(\s*[,}])', r': "\1"\2', s)),
        ]
        
        for fix_func in fixes:
            try:
                fixed_json = fix_func(json_str)
                return json.loads(fixed_json)
            except json.JSONDecodeError:
                pass
        
        # Handle tool-specific response format issues
        tool_patterns = {
            # Handle validation result format
            "validation": re.compile(r'"is_valid":\s*(true|false)', re.IGNORECASE),
            
            # Handle tool output format with special characters
            "tool_output": re.compile(r'"output":\s*({.*?}|\[.*?\])', re.DOTALL)
        }
        
        for pattern_name, pattern in tool_patterns.items():
            if pattern.search(json_str):
                try:
                    # For validation results, ensure boolean values are properly formatted
                    if pattern_name == "validation":
                        json_str = re.sub(r'"is_valid":\s*true', r'"is_valid": true', json_str, flags=re.IGNORECASE)
                        json_str = re.sub(r'"is_valid":\s*false', r'"is_valid": false', json_str, flags=re.IGNORECASE)
                        
                    # Make another attempt with the fixed string
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
        
        # If standard fixes don't work, try a custom extraction approach
        try:
            result = {}
            # Match key-value pairs with more flexible pattern
            pattern = r'"([^"]+)"\s*:\s*(?:"((?:[^"\\]|\\.)*?)"|(\[[^\]]*\])|({[^}]*})|([^,}\]]+))'
            matches = re.finditer(pattern, json_str, re.DOTALL)
            
            for match in matches:
                key = match.group(1)
                # Get the first non-None capture group for value
                value = next(item for item in match.groups()[1:] if item is not None)
                
                # Try to convert to appropriate Python type
                try:
                    # Handle arrays and objects
                    if value.startswith('[') or value.startswith('{'):
                        result[key] = json.loads(value)
                    else:
                        # Try to interpret as Python literal
                        try:
                            result[key] = ast.literal_eval(value)
                        except (SyntaxError, ValueError):
                            result[key] = value
                except json.JSONDecodeError:
                    result[key] = value
            
            if result:
                return result
        except Exception:
            pass
        
        # Last resort: Try Python's ast module to evaluate the JSON as a Python dict
        try:
            # Make it more Python-like
            python_dict_str = json_str.replace('null', 'None').replace('true', 'True').replace('false', 'False')
            return ast.literal_eval(python_dict_str)
        except (SyntaxError, ValueError):
            pass
        
        # If all else fails, try to extract fields manually with regex
        try:
            result = {}
            key_pattern = r'"([^"]+)"\s*:'
            keys = re.findall(key_pattern, json_str)
            
            for i, key in enumerate(keys):
                start_idx = json_str.find(f'"{key}"') + len(key) + 3
                end_idx = len(json_str)
                
                if i < len(keys) - 1:
                    next_key = keys[i+1]
                    next_key_idx = json_str.find(f'"{next_key}"')
                    if next_key_idx > start_idx:
                        end_idx = next_key_idx
                
                value_str = json_str[start_idx:end_idx].strip()
                if value_str.endswith(','):
                    value_str = value_str[:-1]
                    
                # Clean up the value string
                if value_str.startswith('"') and value_str.endswith('"'):
                    value_str = value_str[1:-1]
                
                result[key] = value_str
            
            if result:
                return result
        except Exception:
            pass
        
        # If everything failed, give detailed error message
        raise ValueError(f"Failed to parse JSON after multiple attempts. Original response: {llm_response[:100]}...")
        
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

    
    def generate_template(self, subgoals, tool_dependencies, context, persona, llm):
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
            subgoals={subgoals}
            tool_dependencies={tool_dependencies}
            context={context}

            ## Instructions ##
            Your goal is to convert each subgoal into a natural-sounding question template that:
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
            Return a list of question templates, one for each subgoal.

            Example format:
            ```json
            
            "template_questions": [
                "What issues did the customer face with <product>?",
                "Is <product> compatible with <device>?",
                "What resolution options were provided to the customer for <issue>?"
            ]
            
        """
        
        
        response = llm.claude(prompt)
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

    
    def generate_task(self, data_chain, primary_goal, subgoals, tool_dependencies, templates, context, persona, llm):
        """
        Generate an optimized prompt for the specified task description.

        This method creates and optionally optimizes a prompt based on the task description.

        Args:
            task_description (str): Description of the task for which to generate a prompt.
            optimize (bool): Whether to optimize the prompt using MIPROv2.

        Returns:
            str: The generated prompt history.
        """

        prompt=f"""You are a Human Software Engineer tasked with curating high-quality, structured issue resolution workflows that reflect realistic software development practices.

            # Input:
            persona={persona}
            data_chain={data_chain}
            primary_goal={primary_goal}
            subgoals={subgoals}
            tool_dependencies={tool_dependencies}
            templates={templates}
            context={context}

            ## Instructions ##

            Your objective is to simulate a **realistic software engineering task** that begins with a GitHub issue and ends with a viable code-level resolution. Your answers should reflect how a capable developer would interpret the issue, explore related code, understand the surrounding logic, and generate a final patch that would resolve the issue.

            ### Step 1: Define the task ###
            - Frame a **developer-level objective** from the `primary_goal`, posed as a task a contributor or maintainer might take on in a professional project setting.
            - This task should mirror realistic SWE-bench problems: resolving a GitHub issue in a specific repo by understanding the context and generating a **code patch**.
            - Avoid generic or academic phrasing. Be concrete and focused on code outcomes.

            ### Step 2: Generate subtasks ###
            For each subgoal:
            - Ground the corresponding template into a **realistic engineering sub-question**, using only what's available in `context` (e.g., issue title, description, related PRs, file names, stack traces, code references).
            - Select the corresponding `tool_dependency` and appropriate `data_chain` stage.
            - Return a `subtask_ground_truth` as a **Git-style code patch**, using the following format:

            --- a/<filename> +++ b/<filename> @@ <line context>

            <line(s) removed>

            <line(s) added>

            markdown
            Copy
            Edit

            This patch should:
            - Reflect the actual change a developer would make to partially resolve the issue.
            - Be realistic, minimal, and **copy-pasteable as part of a GitHub pull request**.
            - Include at least a few lines of context for readability and review.

            Also include a `thinking_trace` to justify the change:
            > "To answer this subgoal, we use <tool_dependency> on <data_chain stage> to extract <code-relevant insight>."

            Each subtask must contain:
            - `subgoal`
            - `question` (grounded from template)
            - `subtask_ground_truth` (GitHub-style patch)
            - `thinking_trace`
            - `data source` (stage from `data_chain`)

            ### Step 3: Define subtask dependencies ###
            - Express any **logical or sequential dependencies** using a directed graph format, such as `1 → 2` or `1,3 → 4`.
            - These dependencies should reflect how subtasks rely on prior steps for inputs, decisions, or context.

            ### Step 4: Final patch (`ground_truth`) ###
            - Based on the subtask patches, synthesize a full `ground_truth` patch representing the **complete fix** for the GitHub issue.
            - This should be a full, cohesive **code patch**—just like what a developer would submit in a GitHub PR.
            - It must:
            - Be grounded entirely in `context`.
            - Include `diff` blocks with `+` (inserted) and `-` (removed) lines.
            - Have sufficient surrounding lines for context (`@@` if needed).
            - Focus on fixing the issue — whether it's a bug, enhancement, or broken logic.
            - Include **all subtasks' changes merged into one patch** (if they are in the same file, grouped; if in different files, separated).

            ## Guidelines ##
            - Do **not** fabricate code, filenames, or logic beyond what's given in `context`.
            - Each `subtask_ground_truth` and the final `ground_truth` must resemble **realistic GitHub code patches**.
            - Use Git diff format (lines added with `+`, removed with `-`, preserve indentation).
            - Do not use vague answers. Be exact and code-precise.
            - Maintain the tone of an experienced software engineer submitting a professional fix.

            ## Output Format ##
            ```json
            "task": "<clear issue-resolution task as a SWE might define it>",
            "subtasks": [
                
                    "subgoal": "<subgoal 1>",
                    "question": "<question grounded from template>",
                    "subtask_ground_truth": "<GitHub-style code patch with --- a/..., +++ b/... format>",
                    "thinking_trace": "To answer this subgoal, we use <tool_dependency> on <data_chain stage> to extract <code-relevant insight>.",
                    "data source": "<data_chain stage>"
                ,
                ...
            ],
            "dependency_graph": "<logical flow of subtasks (e.g., 1->2; 1,3->4)>",
            "ground_truth": "<final, merged GitHub-style code patch that resolves the issue>"

        """
        
        
        response = llm.claude(prompt)
        return response
           