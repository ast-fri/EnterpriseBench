import boto3
import json
import time
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain.schema import HumanMessage
import os
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
from langchain_huggingface import HuggingFacePipeline, ChatHuggingFace
from google import genai
from google.genai import types
import base64
import requests

from dotenv import load_dotenv
load_dotenv()

class LLM_factory:
    def __init__(self, use_vllm=True, vllm_url="http://localhost:8001/v1/", 
                 model_path=None, model_name="qwen3-8b"):
        """
        Unified factory supporting both vLLM and regular inference
        
        Args:
            use_vllm: If True, use vLLM server; if False, use HuggingFace
            vllm_url: URL of vLLM server
            model_path: Path for HuggingFace (ignored if use_vllm=True)
            model_name: Model identifier
        """
        self.use_vllm = use_vllm
        self.vllm_url = vllm_url
        self.model_name = ""
        if use_vllm:
            # Use vLLM via OpenAI-compatible API
            self.chat_model = ChatOpenAI(
                model=self.model_name,
                openai_api_key="EMPTY",
                openai_api_base=vllm_url,
                max_tokens=1024,
                temperature=0.7,
                model_kwargs={
                    "extra_body": {
                        "chat_template_kwargs": {
                            "enable_thinking": False  # ← Disable thinking
                        }
                    }
                }
            )
        else:
            # Fallback to HuggingFace
            from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
            from langchain_huggingface import HuggingFacePipeline, ChatHuggingFace
            import torch
            
            tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.bfloat16,
                device_map="auto",
                trust_remote_code=True
            )
            
            pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=512,
                temperature=0.7,
            )
            
            llm = HuggingFacePipeline(pipeline=pipe)
            self.chat_model = ChatHuggingFace(llm=llm)
    
    def _convert_to_langchain_messages(self, messages):
        """Convert message list to LangChain format"""
        langchain_messages = []
        
        for msg in messages:
            role = msg.get('role')
            content = msg.get('content', '')
            
            if role == 'system':
                langchain_messages.append(SystemMessage(content=content))
            elif role == 'user':
                langchain_messages.append(HumanMessage(content=content))
            elif role == 'assistant':
                if 'tool_calls' in msg:
                    langchain_messages.append(AIMessage(
                        content=content,
                        additional_kwargs={'tool_calls': msg['tool_calls']}
                    ))
                else:
                    langchain_messages.append(AIMessage(content=content))
            elif role == 'tool':
                langchain_messages.append(ToolMessage(
                    content=content,
                    name=msg.get('name', 'unknown'),
                    tool_call_id=msg.get('tool_call_id', f"call_{msg.get('name', 'unknown')}")
                ))
        
        return langchain_messages
    def format_messages_for_vllm(self, messages):
        """
        Convert multi-turn conversation to system + user format only
        
        This ensures maximum compatibility with vLLM chat API
        """
        # Extract system message
        system_content = None
        
        for msg in messages:
            if msg.get('role') == 'system':
                system_content = msg.get('content', '')
                break
        
        # Build conversation history as a single user message
        conversation_history = []
        
        for msg in messages:
            role = msg.get('role')
            content = msg.get('content', '')
            
            if role == 'system':
                continue  # Already extracted
            
            elif role == 'user':
                conversation_history.append(f"User: {content}")
            
            elif role == 'assistant':
                # Check if it has tool calls
                if 'tool_calls' in msg and msg['tool_calls']:
                    tool_call = msg['tool_calls'][0]['function']
                    tool_name = tool_call['name']
                    tool_args = tool_call.get('arguments', {})
                    
                    # Format tool call in conversation
                    conversation_history.append(
                        f"Assistant called tool: {tool_name}\n"
                        f"Arguments: {json.dumps(tool_args)}"
                    )
                elif content:
                    conversation_history.append(f"Assistant: {content}")
            
            elif role == 'tool':
                tool_name = msg.get('name', 'unknown_tool')
                tool_output = content
                
                conversation_history.append(
                    f"Tool {tool_name} returned:\n{tool_output}"
                )
        
        # Build final messages
        formatted_messages = []
        
        if system_content:
            formatted_messages.append({
                'role': 'system',
                'content': system_content
            })
        
        # Combine all conversation history into a single user message
        if conversation_history:
            combined_history = '\n\n'.join(conversation_history)
            formatted_messages.append({
                'role': 'user',
                'content': combined_history
            })
        
        return formatted_messages
    def local(self, messages):
        """
        Generate response using local model (Qwen-8B) via ChatHuggingFace

        Args:
        messages: List of message dicts with 'role' and 'content'

        Returns:
        AIMessage with generated content
        """
        if not self.chat_model:
            raise ValueError("Local model not initialized. Provide model_path in constructor.")

        # Convert to LangChain format
        # langchain_messages = self._convert_to_langchain_messages(messages)

        max_retries = 3
        retries = 0
        # text = self.tokenizer.apply_chat_template(
        #     messages,
        #     tokenize=False,
        #     add_generation_prompt=True,
        #     enable_thinking=False # Switches between thinking and non-thinking modes. Default is True.
        # )
        # text = self.format_messages_for_vllm(messages)
        while retries < max_retries:
            try:
                # Invoke ChatHuggingFace
                
                response = self.chat_model.invoke(messages)
                return response
            except Exception as e:
                retries += 1
                print(f"Failed Message: {messages}")
                print(f"Local model attempt {retries} failed: {str(e)}")
                if retries < max_retries:
                    time.sleep(2)
                else:
                    print(f"All retries failed. Returning empty response.")
            return AIMessage(content="")

        return AIMessage(content="")
    def claude(self, message):
        max_retries = 5  # Maximum number of retry attempts
        retries = 0
        
        while retries < max_retries:
            try:
                AWS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
                AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
                AWS_REGION = os.getenv("AWS_REGION")
                
                modelId = 'anthropic.claude-3-5-sonnet-20241022-v2:0'
                
                temperature = 0
                top_p = 1
                max_tokens_to_generate = 10000
                
                system_prompt = "All your responses should be in json format"
                messages = [{"role":"user", "content": message}]

                bedrock_runtime = boto3.client(
                    service_name='bedrock-runtime',
                    region_name=AWS_REGION,
                    aws_access_key_id=AWS_KEY,
                    aws_secret_access_key=AWS_SECRET_KEY,
                ) 
                
                body = json.dumps({
                        "messages": messages,
                        "system": system_prompt,
                        "max_tokens": max_tokens_to_generate,
                        "temperature": temperature,
                        "top_p": top_p,
                        "anthropic_version": "bedrock-2023-05-31"
                })
                
                response = bedrock_runtime.invoke_model(
                    modelId=modelId,
                    body=body,
                )
                response_body = json.loads(response.get('body').read())
                result = response_body.get('content', '')
                return result[0]["text"]
                
            except Exception as e:
                retries += 1
                # Wait for 15 minutes (900 seconds)
                wait_time = 900
                if retries >= max_retries:
                    print(f"Failed after {max_retries} attempts: {str(e)}")
                    return ""  # Return empty string after all retries fail
                print(f"Error occurred while calling Claude: {str(e)}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

    def gpt(self,message):
        api_key_azure_ai = os.getenv("AZURE_API_KEY")
        api_base_azure_ai = os.getenv("AZURE_API_ENDPOINT")
        api_key_azure_chat = os.getenv("AZURE_CHAT_API_KEY")
        api_base_azure_chat = os.getenv("AZURE_CHAT_ENDPOINT")
        
        ## FOR AZURE AI
        # llm_azure = AzureChatOpenAI(
        #         api_key=api_key_azure_ai,  # Replace with your actual API key
        #         api_version="2024-08-01-preview",
        #         azure_endpoint=api_base_azure_ai,
        #         model_name="gpt-4o",
        #     )
        

        ## FOR AZURE CHAT
        llm_azure = AzureChatOpenAI(
                api_key=api_key_azure_chat,  # Replace with your actual API key
                api_version="2024-10-21",
                azure_endpoint=api_base_azure_chat,
                model_name="gpt-4o",
            )
        max_retries = 5
        retries = 0
        
        while retries < max_retries:
            try:
                messages = [HumanMessage(content=message)]
                # print("Length of message", len(message))
                # Call the model correctly
                response = llm_azure.invoke(message)
                
                return response
            except Exception as e:
                retries += 1
                time_wait = 15 * retries
                print(f"Failed on Message: {message}")
                print(f"Error occurred: {str(e)}. Retrying in {time_wait} seconds...")
                time.sleep(time_wait)

        return {"response_metadata": "", "content": ""}  # If all retries fail, return an empty string
    
    def gemini(self,message):
        # Initialize the GenAI client
        client = genai.Client(
            vertexai=True,
            project="genai-gemini-testing",
            location="global",
        )


        model = "gemini-2.5-pro"
        contents = [
            types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=message)
            ]
            ),
        ]

        generate_content_config = types.GenerateContentConfig(
            temperature = 1,
            top_p = 1,
            seed = 0,
            max_output_tokens = 65535,
            safety_settings = [types.SafetySetting(
            category="HARM_CATEGORY_HATE_SPEECH",
            threshold="OFF"
            ),types.SafetySetting(
            category="HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold="OFF"
            ),types.SafetySetting(
            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
            threshold="OFF"
            ),types.SafetySetting(
            category="HARM_CATEGORY_HARASSMENT",
            threshold="OFF"
            )],
            thinking_config=types.ThinkingConfig(
            thinking_budget=-1,
            ),
        )
        max_retries = 5
        retries = 0

        while retries < max_retries:
            try:
                # Generate content using the client
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=generate_content_config,
                )
                return response.text
            except Exception as e:
                retries += 1
                # Wait for 15 minutes (900 seconds)
                wait_time = 15 * retries
                print(f"""Error occurred while calling Gemini: {str(e)}. Retrying in {
                wait_time} seconds...""")
                time.sleep(wait_time)
                
        return {"response_metadata": "", "content": ""}  # If all retries fail, return an empty string
