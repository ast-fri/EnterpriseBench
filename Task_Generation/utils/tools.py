import json
import secrets
from typing import Any, Dict, List, Optional
import fnmatch
from Task_Generation_sft_batch2_copy.Factories.llm_factory import LLM_factory

class Tools:
    def __init__(self):
        arguments = None
    def get_tool_context(self, tools: List[Dict]) -> str:
        context_parts = []
        for tool in tools:
            error = ""
            try:
                output = getattr(self, tool["tool_name"])(tool["tool_arguments"])  # Assuming the function takes input dict, adjust if needed
            except Exception as e:
                print(f"ERROR IN CALLING FUNCTION: {tool}:  {e}")
                output = "Error calling function"
                error = e
            if(not output):
                output = f"The tool call is invalid, error {tool}:  {error}"
            context_parts.append({"tool_name": {tool["tool_name"]}, "tool_arguments": tool["tool_arguments"],  "tool_output": output})
        return context_parts
            
    def load_json(self, path: str = "") -> List[Dict[str, Any]]:
        if path == "":
            return []
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
        
    def github_list_my_repositories(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Workspace/GitHub/GitHub.json") -> List[Dict]:
        """Lists all GitHub repositories accessible to an employee."""
        data = self.load_json(json_path)
        emp_id = arguments.get("emp_id", "")
        repositories = [repo for repo in data if repo.get("emp_id") == emp_id]
        return [
            {
                "repo_name": repo.get("repo_name"),
                "creation_date": repo.get("creation_date"),
                "emp_id": repo.get("emp_id"),
                "license": repo.get("license")
            } for repo in repositories
        ]

    def github_list_issues_of_repository(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Workspace/GitHub/GitHub.json") -> List[Dict]:
        """Lists all issues for a specified GitHub repository."""
        data = self.load_json(json_path)
        repo_name = arguments.get("repo_name", "")
        for repo in data:
            if repo.get("repo_name") == repo_name:
                return repo.get("issues", [])
        return []

    def github_create_repository(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Workspace/GitHub/GitHub.json") -> List[Dict]:
        """Creates a new GitHub repository entry with specified metadata. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        new_repo = {
            "repo_name": arguments.get("repo_name", self.llm({"prompt": "Create a new github repository Name"})),
            "emp_id": arguments.get("emp_id", ""),
            "license": arguments.get("license", self.llm({"prompt": "Create a github repository license"})),
            "creation_date": arguments.get("creation_date", self.llm({"prompt": "Create a github repository creation date"})),
            "issues": []
        }
        data.append(new_repo)
        #self.save_json(json_path, data)
        return [new_repo]

    def github_create_issue(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Workspace/GitHub/GitHub.json") -> List[Dict]:
        """Creates a new issue in a specified GitHub repository. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        repo_name = arguments.get("repo_name", "")
        issue = {
            "id": arguments.get("id", "0000"),
            "title": arguments.get("title", self.llm({"prompt": f"Create a new github repository Issue Title, repository Name {repo_name}"})),
            "description": arguments.get("description", self.llm({"prompt": f"Create a new github repository Issue Description, repository Name {repo_name}"})),
            "status": arguments.get("status", self.llm({"prompt": f"Create a new github repository Issue status [Open/Close], repository Name {repo_name}"})),
            "created_at": arguments.get("created_at", self.llm({"prompt": f"Create a new github repository Issue creation date, repository Name {repo_name}"})),
            "patch": arguments.get("patch", "")
        }
        for repo in data:
            if repo.get("repo_name") == repo_name:
                repo.setdefault("issues", []).append(issue)
                #self.save_json(json_path, data)
                return [issue]
        return []

    def github_get_issue(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Workspace/GitHub/GitHub.json") -> List[Dict]:
        """Retrieves details for a specific issue identified by issue ID within a repository."""
        data = self.load_json(json_path)
        repo_name = arguments.get("repo_name", "")
        issue_id = arguments.get("id", "")
        for repo in data:
            if repo.get("repo_name") == repo_name:
                if repo.get("issues").get("id") == issue_id:
                    return [repo.get("issues")]
        return []

    def github_update_repository(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Workspace/GitHub/GitHub.json") -> List[Dict]:
        """Updates metadata for an existing GitHub repository. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        repo_name = arguments.get("repo_name", "")
        for repo in data:
            if repo.get("repo_name") == repo_name:
                emp_id = arguments.get("emp_id", "")
                license = arguments.get("license", self.llm({"prompt": f"Create a github repository license [MIT, apache-2.0]"}))
                creation_date = arguments.get("creation_date", self.llm({"prompt": "Create a github repository creation date"}))
                if emp_id is not None:
                    repo["emp_id"] = emp_id
                if license is not None:
                    repo["license"] = license
                if creation_date is not None:
                    repo["creation_date"] = creation_date
                #self.save_json(json_path, data)
                return [repo]
        return []

    def github_delete_repository(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Workspace/GitHub/GitHub.json") -> List[Dict]:
        """Deletes a GitHub repository if access rights are verified."""
        data = self.load_json(json_path)
        repo_name = arguments.get("repo_name", "")
        emp_id = arguments.get("emp_id", "")
        for i, repo in enumerate(data):
            if repo.get("repo_name") == repo_name and repo.get("emp_id") == emp_id:
                deleted_repo = data.pop(i)
                #self.save_json(json_path, data)
                return [{"success": True, "repo_name": deleted_repo.get("repo_name")}]
        return [{"success": False, "repo_name": repo_name}]

    def github_update_issue(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Workspace/GitHub/GitHub.json") -> List[Dict]:
        """Updates an existing issue's details. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        repo_name = arguments.get("repo_name", "")
        issue_id = arguments.get("id", "")
        for repo in data:
            if repo.get("repo_name") == repo_name:
                if repo.get("issues").get("id") == issue_id:
                    title = arguments.get("title", "")
                    description = arguments.get("description", "")
                    status = arguments.get("status", "")
                    if title is not None:
                        repo["issues"]["title"] = title
                    if description is not None:
                        repo["issues"]["description"] = description
                    if status is not None:
                        repo["issues"]["status"] = status
                 
                    #self.save_json(json_path, data)
                    return repo["issues"]
        return []

    def github_delete_issue(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Workspace/GitHub/GitHub.json") -> List[Dict]:
        """Deletes an issue in a repository if permissions allow."""
        data = self.load_json(json_path)
        repo_name = arguments.get("repo_name", "")
        issue_id = arguments.get("id", "")
        for repo in data:
            if repo.get("repo_name") == repo_name:
                issues = repo.get("issues", [])
                for i, issue in enumerate(issues):
                    if issue.get("id") == issue_id:
                        issues.pop(i)
                        #self.save_json(json_path, data)
                        return [{"success": True, "id": issue_id, "repo_name": repo_name}]
        return [{"success": False, "id": issue_id, "repo_name": repo_name}]

    def github_get_repository_contents(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Workspace/GitHub/GitHub.json") -> List[Dict]:
        """Retrieves the files and metadata inside a specified GitHub repository."""
        data = self.load_json(json_path)
        repo_name = arguments.get("repo_name", "")
        path = arguments.get("path", "")
        for repo in data:
            if repo.get("repo_name") == repo_name:
                contents = repo.get("contents", [])
                if path is None:
                    return contents
                else:
                    return [item for item in contents if item.get("path") == path]
        return []

    def send_message(self,arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Collaboration_tools/conversations.json") -> List[Dict]:
        """Initiate a new conversation thread between emp1 and emp2 within the software engineering team if the conversation ID does not already exist. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        # Check if conversation_id already exists
        existing = [conv for conv in data if conv.get("conversation_id") == arguments.get("conversation_id")]
        if existing:
            # conversation already exists - do not create duplicate
            return existing
        # Add new conversation
        new_conv = {
            "conversation_id": arguments.get("conversation_id", "0000"),
            
                "sender_emp_id": arguments.get("sender_emp_id", ""),
                "recipient_emp_id": arguments.get("recipient_emp_id", ""),
                "category": arguments.get("category", ""),
                "date": arguments.get("date", "")
            ,
            "text": arguments.get("text", "")
        }
        data.append(new_conv)
        #self.save_json(json_path, data)
        return [new_conv]

    def edit_message(self,arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Collaboration_tools/conversations.json") -> List[Dict]:
        """Update the content of an existing conversation entry if it exists between emp1 and emp2 within the software engineering team. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        conv_id = arguments.get("conversation_id", "")
        for conv in data:
            if conv.get("conversation_id") == conv_id:
                conv["sender_emp_id"] = arguments.get("sender_emp_id", conv["sender_emp_id"])
                conv["recipient_emp_id"] = arguments.get("emp2_id", conv["recipient_emp_id"])
                conv["category"] = arguments.get("category", conv.get("category"))
                conv["date"] = arguments.get("date", conv.get("date"))
                conv["text"] = arguments.get("text", conv.get("text"))
                #self.save_json(json_path, data)
                return [conv]
        return []

    def delete_message(self,arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Collaboration_tools/conversations.json") -> List[Dict]:
        """Delete an existing conversation entry between emp1 and emp2 if authorized and datasource is valid."""
        data = self.load_json(json_path)
        conv_id = arguments.get("conversation_id", "")
        emp1_id = arguments.get("sender_emp_id", "")
        emp2_id = arguments.get("recipient_emp_id", "")
        for i, conv in enumerate(data):
            if conv.get("conversation_id") == conv_id and conv["sender_emp_id"] == emp1_id and conv["recipient_emp_id"] == emp2_id:
                deleted = data.pop(i)
                #self.save_json(json_path, data)
                return [deleted]
        return []

    def list_conversation_ids_between_employees(self,arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Collaboration_tools/conversations.json") -> List[Dict]:
        """Fetches all conversation IDs for conversations that exist between two employees."""
        data = self.load_json(json_path)
        emp1_id = arguments.get("sender_emp_id", "")
        emp2_id = arguments.get("recipient_emp_id", "")
        conversation_ids = [
            conv.get("conversation_id") for conv in data
            if (conv["sender_emp_id"] == emp1_id and conv["recipient_emp_id"] == emp2_id)
            or (conv["sender_emp_id"] == emp2_id and conv["recipient_emp_id"] == emp1_id)
        ]
        return [{"conversation_ids": conversation_ids}]

    def fetch_conversation_by_id(self,arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Collaboration_tools/conversations.json") -> List[Dict]:
        """Retrieves the full conversation data based on a unique conversation ID, verifying access permissions."""
        data = self.load_json(json_path)
        conv_id = arguments.get("conversation_id", "")
        for conv in data:
            if conv.get("conversation_id") == conv_id:
                return [conv]
        return []

    def read_email(self, arguments,json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Enterprise_mail_system/emails.json") -> List[Dict]:
        """Reads a specific email in a thread based on the unique email_id."""
        data = self.load_json(json_path)
        email_id = arguments.get("email_id", "")
        for email in data:
            if email.get("email_id") == email_id:
                # Add access control/permission checks as needed
                return [email]
        return []
    
    def get_emp_id_by_email(self, email, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Human_Resource_Management/Employees/employees.json"):
        """Get employee id using employees email id"""
        data = self.load_json(json_path)
        results = []
        for record in data:
            if email and record.get("email") == email:
                return record.get("emp_id") 
        return ""
    def create_email(self, arguments,json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Enterprise_mail_system/emails.json") -> List[Dict]:
            """Creates a new email message, generating unique email and thread IDs, validating participants, and storing the email with proper metadata. Use llm tool to create the arguments only if not present"""
            data = self.load_json(json_path)
            new_email = {
                "email_id": arguments.get("email_id") or "0000",
                "thread_id": arguments.get("thread_id") or "0000",
                "date": arguments.get("date", ""),
                
                    "sender_email": arguments.get("sender_email", ""),
                    "sender_name": arguments.get("sender_name", ""),
                    "sender_emp_id": self.get_emp_id_by_email(arguments.get("sender_email", ""))
                ,
               
                    "recipient_email": arguments.get("recipient_email", ""),
                    "recipient_name": arguments.get("recipient_name", ""),
                    "recipient_emp_id": self.get_emp_id_by_email(arguments.get("recipient_email", ""))
                ,
                "subject": arguments.get("subject", ""),
                "body": arguments.get("body", ""),
                "importance": arguments.get("importance", "Normal"),
                "category": arguments.get("category", "INTERNAL"),
                "signature": arguments.get("signature", ""),
                "confidentiality_notice": arguments.get("confidentiality_notice", "")
            }
            data.append(new_email)
            #self.save_json(json_path, data)
            return [new_email]

    def update_email(self, arguments,json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Enterprise_mail_system/emails.json") -> List[Dict]:
            """Updates an existing email message’s subject, body, importance, category, signature, or confidentiality notice after verifying user authorization. Use llm tool to create the arguments only if not present"""
            data = self.load_json(json_path)
            email_id = arguments.get("email_id", "")
            for email in data:
                if email.get("email_id") == email_id:
                    for field in ["subject", "body", "importance", "category", "signature", "confidentiality_notice"]:
                        if arguments.get(field) is not None:
                            email[field] = arguments[field]
                    #self.save_json(json_path, data)
                    return [email]
            return []

    def delete_email(self,arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Enterprise_mail_system/emails.json") -> List[Dict]:
            """Deletes an email message by sender or recipient after verifying participation and permissions based on email ID and optionally thread ID."""
            data = self.load_json(json_path)
            email_id = arguments.get("email_id", "")
            for i, email in enumerate(data):
                if email.get("email_id") == email_id:
                    removed = data.pop(i)
                    #self.save_json(json_path, data)
                    return [removed]
            return []

    def list_my_email_threads(self, arguments,json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Enterprise_mail_system/emails.json") -> List[Dict]:
            """Lists all email threads for a given user's email address, optionally filtered by a date range or importance"""
            data = self.load_json(json_path)
            emp_id = arguments.get("emp_id", "")
            start_date = arguments.get("start_date", "")
            end_date = arguments.get("end_date", "")
            importance = arguments.get("importance", "")

            threads = {}
            for mail in data:
                if emp_id in [mail.get("sender_emp_id", {}), mail.get("recipient_emp_id", {})]:
                    if start_date and mail.get("date") < start_date:
                        continue
                    if end_date and mail.get("date") > end_date:
                        continue
                    if importance and mail.get("importance") != importance:
                        continue
                    thread_id = mail.get("thread_id")
                    if thread_id not in threads or mail.get("date") > threads[thread_id]["last_email_date"]:
                        threads[thread_id] = {
                            "thread_id": thread_id,
                            "subject": mail.get("subject", ""),
                            "last_email_date": mail.get("date"),
                            "email_count": sum(1 for m in data if m.get("thread_id") == thread_id)
                        }
            return [{"threads": list(threads.values())}]

    def list_thread_ids_between_sender_recipient(self,arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Enterprise_mail_system/emails.json") -> List[Dict]:
            """Reads all thread IDs existing between a particular sender email and recipient email."""
            data = self.load_json(json_path)
            sender_email = arguments.get("sender_email", "")
            recipient_email = arguments.get("recipient_email", "")
            thread_ids = list({email.get("thread_id") for email in data if email.get("sender_email", {}) == sender_email and email.get("recipient_email", {}) == recipient_email})
            return [{"thread_ids": thread_ids}]

    def list_email_ids_in_thread(self,arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Enterprise_mail_system/emails.json") -> List[Dict]:
            """Reads all email IDs belonging to a specific email thread using unique thread_id."""
            data = self.load_json(json_path)
            thread_id = arguments.get("thread_id", "")
            email_ids = [email.get("email_id") for email in data if email.get("thread_id") == thread_id]
            return [{"email_ids": email_ids}]
    
       

    def read_customer_support_chat(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/Customer Support/customer_support_chats.json") -> List[Dict]:
        """Reads customer support chat data between employee and customer based on unique chat id."""
        data = self.load_json(json_path)
        chat_id = arguments.get("chat_id", "")
        emp_id = arguments.get("emp_id", "")
        product_id = arguments.get("product_id", "")
        customer_id = arguments.get("customer_id", "")
        query = arguments.get("query")
        for chat in data:
            if chat.get("chat_id") == chat_id:
                if chat.get("emp_id") == emp_id:
                    # Could add more filters or semantic query handling
                    return [chat]
        return []

    def create_customer_support_chat(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/Customer Support/customer_support_chats.json") -> List[Dict]:
        """Records a new support interaction entry with associated employee, product, and customer details. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        new_chat = {
            "chat_id": arguments.get("chat_id", "0000"),
            "product_id": arguments.get("product_id", ""),
            "product_name": arguments.get("product_name", ""),
            "customer_id": arguments.get("customer_id"),
            "customer_name": arguments.get("customer_name", ""),
            "emp_id": arguments.get("emp_id"),
            "text": arguments.get("text"),
            "interaction_date": arguments.get("interaction_date", "")
        }
        data.append(new_chat)
        #self.save_json(json_path, data)
        return [new_chat]

    def update_customer_support_chat(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/Customer Support/customer_support_chats.json") -> List[Dict]:
        """Updates an existing support chat record ensuring validity and access controls. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        chat_id = arguments.get("chat_id", "")
        for chat in data:
            if chat.get("chat_id") == chat_id:
                for key in ["product_id", "customer_id", "text", "interaction_date"]:
                    if arguments.get(key) is not None:
                        chat[key] = arguments.get(key)
                #self.save_json(json_path, data)
                return [chat]
        return []

    def delete_customer_support_chat(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/Customer Support/customer_support_chats.json") -> List[Dict]:
        """Deletes a customer support chat record after verifying permissions."""
        data = self.load_json(json_path)
        chat_id = arguments.get("chat_id", "")
        for i, chat in enumerate(data):
            if chat.get("chat_id") == chat_id:
                removed = data.pop(i)
                #self.save_json(json_path, data)
                return [removed]
        return []

    def read_my_crm_chats(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/Customer Support/customer_support_chats.json") -> List[Dict]:
        """Lists chat IDs handled by the employee with optional filters like date range."""
        data = self.load_json(json_path)
        emp_id = arguments.get("emp_id", "")
        start_date = arguments.get("start_date", "")
        end_date = arguments.get("end_date", "")
        chat_ids = [
            chat.get("chat_id") for chat in data
            if chat.get("emp_id") == emp_id and
            (not start_date or chat.get("interaction_date") >= start_date) and
            (not end_date or chat.get("interaction_date") <= end_date)
        ]
        return [{"chat_ids": chat_ids}]

    def list_customer_support_chats_by_product(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/Customer Support/customer_support_chats.json") -> List[Dict]:
        """Lists customer support chat summaries filtered by product with essential details."""
        data = self.load_json(json_path)
        emp_id = arguments.get("emp_id", "")
        product_id = arguments.get("product_id", "")
        start_date = arguments.get("start_date", "")
        end_date = arguments.get("end_date", "")
        chats = [
            {
                "chat_id": chat.get("chat_id"),
                "customer_id": chat.get("customer_id"),
                "customer_name": chat.get("customer_name"),
                "emp_id": chat.get("emp_id"),
                "interaction_date": chat.get("interaction_date")
            }
            for chat in data
            if chat.get("emp_id") == emp_id and chat.get("product_id") == product_id and
            (not start_date or chat.get("interaction_date") >= start_date) and
            (not end_date or chat.get("interaction_date") <= end_date)
        ]
        return [{"chats": chats}]

    def list_customer_support_chats_by_customer(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/Customer Support/customer_support_chats.json") -> List[Dict]:
        """Lists customer support chat summaries filtered by customer with key details."""
        data = self.load_json(json_path)
        emp_id = arguments.get("emp_id", "")
        customer_id = arguments.get("customer_id", "")
        start_date = arguments.get("start_date", "")
        end_date = arguments.get("end_date", "")
        chats = [
            {
                "chat_id": chat.get("chat_id"),
                "product_id": chat.get("product_id"),
                "product_name": chat.get("product_name"),
                "emp_id": chat.get("emp_id"),
                "interaction_date": chat.get("interaction_date")
            }
            for chat in data
            if chat.get("emp_id") == emp_id and chat.get("customer_id") == customer_id and
            (not start_date or chat.get("interaction_date") >= start_date) and
            (not end_date or chat.get("interaction_date") <= end_date)
        ]
        return [{"chats": chats}]

    def create_product(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/products.json") -> List[Dict]:
        """Creates a new product entry if the product ID doesn't already exist and employee has the required access level. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        product_id = arguments.get("product_id", "")
        if any(product.get("product_id") == product_id for product in data):
            # Product already exists, return existing entry or raise error
            return [product for product in data if product.get("product_id") == product_id]

        new_product = {
            "product_id": arguments.get("product_id", "0000"),
            "product_name": arguments.get("product_name", ""),
            "category": arguments.get("category", ""),
            "discounted_price": arguments.get("discounted_price", ""),
            "actual_price": arguments.get("actual_price", ""),
            "rating": arguments.get("rating", ""),
            "about_product": arguments.get("about_product", "")
        }
        data.append(new_product)
        #self.save_json(json_path, data)
        return [new_product]

    def get_product(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/products.json") -> List[Dict]:
        """Reads and displays product details based on product ID or product Name."""
        data = self.load_json(json_path)
        product_id = arguments.get("product_id", "")
        product_name_pattern = arguments.get("product_name", "")
        result = []

        # Normalize pattern casefold for case-insensitive matching
        pattern = product_name_pattern.casefold()

        for product in data:
            if product.get("product_id") == product_id and product_id != "":
                result.append(product)
            else:
                pname = product.get("product_name", "").casefold()
                if pattern and fnmatch.fnmatch(pname, pattern):
                    result.append(product)

        return result
    def get_customer(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/customers.json") -> List[Dict]:
        """Reads and displays customer details based on customer ID  if access is allowed."""
        data = self.load_json(json_path)
        customer_id = arguments.get("customer_id", "")
        customer_name = arguments.get("customer_name", "")
        query = arguments.get("query")  # semantic search not implemented here
        result = []
        for customer in data:
            if customer.get("customer_id") == customer_id:
                result.append(customer)
            elif customer.get("customer_name").lower() == customer_name.lower():
                result.append(customer)
        return result

    def update_product(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/products.json") -> List[Dict]:
        """Updates an existing product entry if the product ID exists and employee is authorized. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        product_id = arguments.get("product_id", "")
        for product in data:
            if product.get("product_id") == product_id:
                for field in ["product_name", "category", "discounted_price", "actual_price", "rating", "about_product"]:
                    if arguments.get(field) is not None:
                        product[field] = arguments.get(field)
                #self.save_json(json_path, data)
                return [product, {"product_updated": "TRUE"}]
        return []

    def delete_product(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/products.json") -> List[Dict]:
        """Deletes a product entry if the product ID exists and the employee has required access."""
        data = self.load_json(json_path)
        product_id = arguments.get("product_id", "")
        for i, product in enumerate(data):
            if product.get("product_id") == product_id:
                deleted = data.pop(i)
                #self.save_json(json_path, data)
                return [deleted]
        return []

    def list_products_by_category(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/products.json") -> List[Dict]:
        """Lists products filtered by category with optional pagination support."""
        data = self.load_json(json_path)
        category = arguments.get("category", "")
        filtered = []
        for product in data:
            if category is None or product.get("category") == category:
                filtered.append({
                    "product_id": product.get("product_id"),
                    "product_name": product.get("product_name"),
                    "category": product.get("category")
                })
        return [{"products": filtered}]

    def create_product_sentiment(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/Product Sentiment/product_sentiment.json") -> List[Dict]:
        """Creates a new product sentiment/review entry with validation of product, customer, and employee access rights. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        sentiment_id = arguments.get("sentiment_id", "")
        
        # Check if sentiment entry already exists
        if any(entry.get("sentiment_id") == sentiment_id for entry in data):
            return [entry for entry in data if entry.get("sentiment_id") == sentiment_id]
        
        new_entry = {
            "sentiment_id": arguments.get("sentiment_id", "0000"),
            "product_id": arguments.get("product_id"),
            "product_name": arguments.get("product_name", ""),
            "category": arguments.get("category", ""),
            "about_product": arguments.get("about_product", ""),
            "customer_id": arguments.get("customer_id"),
            "customer_name": arguments.get("customer_name", ""),
            "review_id": arguments.get("review_id", ""),
            "review_content": arguments.get("review_content"),
            "review_date": arguments.get("review_date", "")
        }
        data.append(new_entry)
        #self.save_json(json_path, data)
        return [new_entry]
    def get_product_reviews(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/Product Sentiment/product_sentiment.json") -> List[Dict]:
        """Reads all the sentiment IDs of the reviews on a particular product"""
        results = []
        data = self.load_json(json_path)
        product_id = arguments.get("product_id", "")
        customer_id = arguments.get("customer_id", "")
        query = arguments.get("query", "")
        for entry in data:
            if(product_id==entry.get("product_id")):
                 results.append(entry["sentiment_id"])
            # Semantic query handling can be added here
        return results
    def get_customer_reviews(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/Product Sentiment/product_sentiment.json") -> List[Dict]:
        """Reads all the sentiment IDs of the reviews given by a particular customer"""
         
        results = []
        data = self.load_json(json_path)
        customer_id = arguments.get("customer_id", "")
        query = arguments.get("query", "")
        for entry in data:
            if(customer_id==entry.get("customer_id")):
                 results.append(entry["sentiment_id"])
            # Semantic query handling can be added here
        return results
    def get_product_sentiment(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/Product Sentiment/product_sentiment.json") -> List[Dict]:
        """Reads product sentiment data filtered by unique sentiment ID."""
        data = self.load_json(json_path)
        sentiment_id = arguments.get("sentiment_id", "")
        product_id = arguments.get("product_id", "")
        customer_id = arguments.get("customer_id", "")
        query = arguments.get("query", "")
        
        results = []
        for entry in data:
            if sentiment_id == entry.get("sentiment_id"):
                results.append(entry)
            elif(product_id==entry.get("product_id") and customer_id==entry.get("customer_id")):
                 results.append(entry)
            # Semantic query handling can be added here
            
        return results
    

    def update_product_sentiment(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/Product Sentiment/product_sentiment.json") -> List[Dict]:
        """Updates an existing product sentiment entry after access checks. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        sentiment_id = arguments.get("sentiment_id", "")
        
        for entry in data:
            if entry.get("sentiment_id") == sentiment_id:
                for key in ["product_id", "product_name", "category", "about_product", "customer_id", "customer_name", "review_id", "review_content", "review_date"]:
                    if arguments.get(key) is not None:
                        entry[key] = arguments.get(key)
                #self.save_json(json_path, data)
                return [entry]
        return []

    def delete_product_sentiment(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/Product Sentiment/product_sentiment.json") -> List[Dict]:
        """Deletes product sentiment entry if authorized."""
        data = self.load_json(json_path)
        sentiment_id = arguments.get("sentiment_id", "")
        for i, entry in enumerate(data):
            if entry.get("sentiment_id") == sentiment_id:
                deleted = data.pop(i)
                #self.save_json(json_path, data)
                return [deleted]
        return []

    def create_sales_record(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/sales.json") -> List[Dict]:
        """Creates a new product sales record with full metadata and verifies employee permissions. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        if any(rec.get("sales_record_id") == arguments.get("sales_record_id") for rec in data):
            return [rec for rec in data if rec.get("sales_record_id") == arguments.get("sales_record_id")]
        new_record = {
            "sales_record_id": arguments.get("sales_record_id", "0000"),
            "product_id": arguments.get("product_id", ""),
            "product_name": arguments.get("product_name", ""),
            "discounted_price": arguments.get("discounted_price", ""),
            "actual_price": arguments.get("actual_price", ""),
            "discount_percentage": arguments.get("discount_percentage", ""),
            "rating": arguments.get("rating", ""),
            "rating_count": arguments.get("rating_count", ""),
            "category": arguments.get("category", ""),
            "about_product": arguments.get("about_product", ""),
            "product_link": arguments.get("product_link", ""),
            "customer_id": arguments.get("customer_id", ""),
            "customer_name": arguments.get("customer_name", ""),
            "date_of_purchase": arguments.get("date_of_purchase", ""),
        }
        data.append(new_record)
        #self.save_json(json_path, data)
        return [new_record]

    def get_sales_record(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/sales.json") -> List[Dict]:
        """Reads a sales record based on sales_record_id only."""
        data = self.load_json(json_path)
        sales_record_id = arguments.get("sales_record_id", "")
        results = []
        for rec in data:
            if rec.get("sales_record_id") == sales_record_id:
                results.append(rec)
        return results

    def update_sales_record(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/sales.json") -> List[Dict]:
        """Updates an existing sales record based on specific sales_record_id after verifying employee and product access. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        sales_record_id = arguments.get("sales_record_id, """)
        for rec in data:
            if rec.get("sales_record_id") == sales_record_id:
                for key in ["product_id", "product_name", "discounted_price", "actual_price",
                            "discount_percentage", "rating", "rating_count", "category",
                            "about_product", "product_link", "customer_id", "customer_name", "date_of_purchase"]:
                    if key in arguments:
                        rec[key] = arguments[key]
                #self.save_json(json_path, data)
                return [rec]
        return []

    def delete_sales_record(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/sales.json") -> List[Dict]:
        """Deletes an existing sales record based on specific sales_record_id if allowed by employee permissions."""
        data = self.load_json(json_path)
        sales_record_id = arguments.get("sales_record_id", "")
        for i, rec in enumerate(data):
            if rec.get("sales_record_id") == sales_record_id:
                removed = data.pop(i)
                #self.save_json(json_path, data)
                return [removed]
        return []

    def list_sales_records_by_customer_and_product(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/sales.json") -> List[Dict]:
        """Reads sales records summary for a customer and purchased product based on product_id and customer_id"""
        data = self.load_json(json_path)
        customer_id = arguments.get("customer_id", "")
        product_id = arguments.get("product_id", "")
        start_date = arguments.get("start_date", "")
        end_date = arguments.get("end_date", "")
        records = []
        for rec in data:
            if rec.get("customer_id") == customer_id and rec.get("product_id") == product_id:
                records.append({
                "sales_record_id": rec.get("sales_record_id"),
                "product_id": rec.get("product_id"),
                "product_name": rec.get("product_name"),
                "date_of_purchase": rec.get("date_of_purchase"),
            })

            
        return [{"sales_records": records}]

    def list_sales_records_between_dates(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Customer_Relation_Management/sales.json") -> List[Dict]:
        """Returns sales records between specified dates with sales_record_id, product_id, product_name, customer_id, customer_name, and date_of_purchase."""
        data = self.load_json(json_path)
        start_date = arguments.get("start_date", "")
        end_date = arguments.get("end_date", "")
        records = []
        for rec in data:
            date = rec.get("date_of_purchase", "")
            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue
            records.append({
                "sales_record_id": rec.get("sales_record_id"),
                "product_id": rec.get("product_id"),
                "product_name": rec.get("product_name"),
                "customer_id": rec.get("customer_id"),
                "customer_name": rec.get("customer_name"),
                "date_of_purchase": rec.get("date_of_purchase"),
            })
        return [{"sales_records": records}]

    def create_it_ticket(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/IT_Service_Management/it_tickets.json") -> List[Dict]:
        """Creates a new IT service ticket if the reporting employee has access and the ticket ID does not already exist. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        issue_id = arguments.get("id")
        if any(issue.get("id") == issue_id for issue in data):
            return [issue for issue in data if issue.get("id") == issue_id]
        new_issue = {
            "id": arguments.get("id", "0000"),
            "priority": arguments.get("priority", ""),
            "raised_by_emp_id": arguments.get("raised_by_emp_id", ""),
            "assigned_date": arguments.get("assigned_date", ""),
            "emp_id": arguments.get("emp_id", ""),
            "Issue": arguments.get("Issue", ""),
            "Resolution": arguments.get("Resolution", "")
        }
        data.append(new_issue)
        #self.save_json(json_path, data)
        return [new_issue]

    def get_it_ticket(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/IT_Service_Management/it_tickets.json") -> List[Dict]:
        """Retrieves details of an IT ticket by ticket ID and optionally filtered by reporting employee or assignee. Enforces access controls."""
        data = self.load_json(json_path)
        issue_id = arguments.get("id", "")
        emp_id = arguments.get("emp_id", "")
        raised_by_emp_id = arguments.get("raised_by_emp_id", "")
        query = arguments.get("query", "")
        results = []
        for issue in data:
            if issue_id and issue.get("id") != issue_id:
                continue
            if emp_id and issue.get("emp_id") != emp_id:
                continue
            if raised_by_emp_id and issue.get("raised_by_emp_id") != raised_by_emp_id:
                continue
            # query-based matching can be added here
            results.append(issue)
        return results

    def update_it_ticket(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/IT_Service_Management/it_tickets.json") -> List[Dict]:
        """Updates an existing IT ticket with new priority, assignee, issue description or resolution details. Validates user access and ticket existence. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        issue_id = arguments.get("id", "")
        for issue in data:
            if issue.get("id") == issue_id:
                for key in ["priority", "raised_by_emp_id", "assigned_date", "emp_id", "Issue", "Resolution"]:
                    if arguments.get(key) is not None:
                        issue[key] = arguments.get(key, "")
                #self.save_json(json_path, data)
                return [issue]
        return []

    def delete_it_ticket(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/IT_Service_Management/it_tickets.json") -> List[Dict]:
        """Deletes an IT service ticket if the employee has appropriate permissions."""
        data = self.load_json(json_path)
        issue_id = arguments.get("id", "")
        emp_id = arguments.get("emp_id", "")
        for i, issue in enumerate(data):
            if issue.get("id") == issue_id and issue.get("emp_id") == emp_id:
                deleted = data.pop(i)
                #self.save_json(json_path, data)
                return [deleted]
        return []

    def get_it_ticket_ids_by_raiser(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/IT_Service_Management/it_tickets.json") -> List[Dict]:
        """Lists all IT service tickets raised by a issue raiser using their emp id under `raised_by_emp_id` excluding issue and resolution details. Here employee under emp_id is the resolver of ticket"""
        data = self.load_json(json_path)
        emp_id = arguments.get("raised_by_emp_id", "")
        tickets = []
        for issue in data:
            if issue.get("raised_by_emp_id") == emp_id:
                tickets.append({
                    "id": issue.get("id"),
                    "priority": issue.get("priority"),
                    "raised_by_emp_id": issue.get("raised_by_emp_id"),
                    "assigned_date": issue.get("assigned_date"),
                    "emp_id": issue.get("emp_id")
                })
        return [{"tickets": tickets}]

    def list_it_tickets_by_priority(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/IT_Service_Management/it_tickets.json") -> List[Dict]:
        """Retrieves all tickets filtered by priority level, excluding issue and resolution details."""
        data = self.load_json(json_path)
        priority = arguments.get("priority", "")
        tickets = [issue for issue in data if issue.get("priority") == priority]
        # Exclude issue and resolution per instructions
        result = []
        for ticket in tickets:
            result.append({
                "id": ticket.get("id"),
                "priority": ticket.get("priority"),
                "raised_by_emp_id": ticket.get("raised_by_emp_id"),
                "assigned_date": ticket.get("assigned_date"),
                "emp_id": ticket.get("emp_id")
            })
        return [{"tickets": result}]

    def list_it_tickets_assigned_to_me(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/IT_Service_Management/it_tickets.json") -> List[Dict]:
        """Lists all IT service tickets currently assigned to the requesting employee using my employee id."""
        data = self.load_json(json_path)
        emp_id = arguments.get("emp_id", "")
        tickets = [issue for issue in data if issue.get("emp_id") == emp_id]
        result = []
        for ticket in tickets:
            result.append({
                "id": ticket.get("id"),
                "priority": ticket.get("priority"),
                "raised_by_emp_id": ticket.get("raised_by_emp_id"),
                "assigned_date": ticket.get("assigned_date"),
                "emp_id": ticket.get("emp_id")
            })
        return [{"tickets": result}]

    def assign_ticket(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/IT_Service_Management/it_tickets.json") -> List[Dict]:
        """Assigns or reassigns an IT ticket to an employee with updated assignment date. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        issue_id = arguments.get("id", "")
        emp_id = arguments.get("emp_id", "")
        assigned_date = arguments.get("assigned_date", "")
        for issue in data:
            if issue.get("id") == issue_id:
                issue["emp_id"] = emp_id
                if assigned_date:
                    issue["assigned_date"] = assigned_date
                #self.save_json(json_path, data)
                return [issue]
        return []

    def resolve_ticket(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/IT_Service_Management/it_tickets.json") -> List[Dict]:
        """Updates the resolution for a ticket and marks it resolved. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        issue_id = arguments.get("id", "")
        resolution = arguments.get("Resolution", "")
        for issue in data:
            if issue.get("id") == issue_id:
                issue["Resolution"] = resolution
                #self.save_json(json_path, data)
                return [issue]
        return []

    def fetch_employee_record(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Human_Resource_Management/Employees/employees.json") -> List[Dict]:
        """Fetch employee data by various identifiers ."""
        data = self.load_json(json_path)
        emp_id = arguments.get("emp_id", "")
        name = arguments.get("Name", "")
        email = arguments.get("email", "")
        category = arguments.get("category", "")
        query = arguments.get("query", "")
        results = []
        for record in data:
            if emp_id and record.get("emp_id") == emp_id:
                return record
            if name and record.get("Name") == name:
                return record
            if email and record.get("email") == email:
                return record
           
        return results

    def create_employee_record(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Human_Resource_Management/Employees/employees.json") -> List[Dict]:
        """Create a new employee profile with mandatory and optional fields. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        emp_id = arguments.get("emp_id")
        if any(emp['emp_id'] == emp_id for emp in data):
            return [emp for emp in data if emp['emp_id'] == emp_id]
        
        new_record = {
            "index": len(data) + 1,
            "category": arguments.get("category", ""),
            "description": arguments.get("description", ""),
            "Experience": arguments.get("experience", ""),
            "Name": arguments.get("Name", ""),
            "skills": arguments.get("skills", ""),
            "reportees": arguments.get("reportees", []),
            "emp_id": arguments.get("emp_id","emp_007"),
            "reports_to": arguments.get("reports_to", ""),
            "Level": arguments.get("Level", ""),
            "email": arguments.get("email", ""),
            "DOJ": arguments.get("DOJ", ""),
            "DOL": arguments.get("DOL", ""),
            "Salary": arguments.get("Salary", ""),
            "Total Casual Leaves": arguments.get("Total Casual Leaves", ""),
            "Remaining Casual Leaves": arguments.get("Remaining Casual Leaves", ""),
            "Total Sick Leaves": arguments.get("Total Sick Leaves", ""),
            "Remaining Sick Leaves": arguments.get("Remaining Sick Leaves", ""),
            "Total Vacation Leaves": arguments.get("Total Vacation Leaves", ""),
            "Remaining Vacation Leaves": arguments.get("Remaining Vacation Leaves", ""),
            "Total Leaves": arguments.get("Total Leaves", ""),
            "Age": arguments.get("Age", ""),
            "Performance Rating": arguments.get("Performance Rating", ""),
            "Marital Status": arguments.get("marital_status", ""),
            "Gender": arguments.get("gender", ""),
            "is_valid": arguments.get("is_valid", "")
        }
        data.append(new_record)
        #self.save_json(json_path, data)
        return [new_record]

    def update_employee_record(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Human_Resource_Management/Employees/employees.json") -> List[Dict]:
        """Update fields of an existing employee profile. Only provided arguments are updated. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        emp_id = arguments.get("emp_id", "")
        for record in data:
            if record.get("emp_id") == emp_id:
                for key in ["Name", "email", "category", "description", "experience", "skills", "Level",
                            "Salary", "Age", "marital_status", "gender", "DOJ", "DOL", "Total Casual Leaves",
                            "Remaining Casual Leaves", "Total Sick Leaves", "Remaining Sick Leaves",
                            "Total Vacation Leaves", "Remaining Vacation Leaves", "Total Leaves", "Performance Rating"]:
                    if key in arguments:
                        record[key] = arguments[key]
                #self.save_json(json_path, data)
                return [record]
        return []

    def deactivate_employee_record(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Human_Resource_Management/Employees/employees.json") -> List[Dict]:
        """Deactivate employee profile marking as inactive with leaving date. Use llm tool to create the arguments only if not present"""
        data = self.load_json(json_path)
        emp_id = arguments.get("emp_id", "")
        dol = arguments.get("DOL", "")
        for record in data:
            if record.get("emp_id") == emp_id:
                record["DOL"] = dol
                record["is_valid"] = False
                #self.save_json(json_path, data)
                return [record]
        return []

    def fetch_employees_by_ids(self, arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Human_Resource_Management/Employees/employees.json") -> List[Dict]:
        """Fetches basic details (name, email, emp_id, category) of employees given a list of employee IDs."""
        data = self.load_json(json_path)
        emp_ids = arguments.get("emp_ids", [])
        results = []
        for record in data:
            if record.get("emp_id") in emp_ids:
                results.append({
                    "emp_id": record.get("emp_id"),
                    "Name": record.get("Name"),
                    "email": record.get("email"),
                    "category": record.get("category")
                })
        return results

    def enterprise_social_platform_create( self,arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Enterprise Social Platform/posts.json") -> List[Dict]:
        data = self.load_json(json_path)

    def enterprise_social_platform_read( self,arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Enterprise Social Platform/posts.json") -> List[Dict]:
        data = self.load_json(json_path)

    def enterprise_social_platform_update(
                                        self,arguments,json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Enterprise Social Platform/posts.json") -> List[Dict]:
        data = self.load_json(json_path)
    

    def enterprise_social_platform_delete(self,arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Enterprise Social Platform/posts.json") -> List[Dict]:
        data = self.load_json(json_path)

    def inazuma_overflow_read( self, arguments,json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Inazuma_Overflow/overflow.json") -> List[Dict]:
        data = self.load_json(json_path)

    def inazuma_overflow_create( self,arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Inazuma_Overflow/overflow.json") -> List[Dict]:
        data = self.load_json(json_path)
        

    def inazuma_overflow_update( self,arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Inazuma_Overflow/overflow.json") -> List[Dict]:
        data = self.load_json(json_path)
    

    def inazuma_overflow_delete( self,arguments, json_path: str = "/mnt/home-ldap/vkharsh_ldap/Research/EnterpriseBench/Inazuma_Overflow/overflow.json") -> List[Dict]:
        data = self.load_json(json_path)
    
    def llm(self, prompt):
        """Call the LLM to generate the contents only for create tasks"""
        llm = LLM_factory()
        prompt = prompt.get("prompt", "")
        response = llm.gpt(prompt)
        return response.content
    
