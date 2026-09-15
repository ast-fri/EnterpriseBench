"""
EnterpriseBench Tool Environment - Production wrapper for your Tools class.

Ported from EnterprisePlatform/train/agentic_training_original/enterprise_tool_environment.py
so that Evaluate/ is self-contained (no runtime dependency on the training repo).
Unlike the training copy, every path here is derived from this file's own location —
Evaluate/ and Task_Generation/ are siblings under EnterpriseBench/, so no user-specific
absolute paths are needed.
"""

import sys
import tempfile
import shutil
import logging
import json
import os
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from data_structures import ToolExecutionResult, ToolExecutionStatus

# EnterpriseBench/Evaluate/enterprise_tool_environment.py -> parent.parent == EnterpriseBench/
_ENTERPRISEBENCH_ROOT = Path(__file__).resolve().parent.parent

# Add the EnterpriseBench tools module path used by the evaluation environment.
sys.path.insert(0, str(_ENTERPRISEBENCH_ROOT / "Task_Generation" / "utils"))

from tools import Tools  # Your existing Tools class

logger = logging.getLogger(__name__)

DEFAULT_ENTERPRISEBENCH_ENV_ROOT = str(_ENTERPRISEBENCH_ROOT)
ENTERPRISEBENCH_PATH_ALIASES = (
    DEFAULT_ENTERPRISEBENCH_ENV_ROOT,
)
ENTERPRISEBENCH_TOOLS_JSON_PATH = _ENTERPRISEBENCH_ROOT / "Task_Generation" / "utils" / "tools.json"

class EnterpriseBenchToolEnvironment:
    """
    Production wrapper for EnterpriseBench tools.

    Integrates your existing Tools class with the evaluation pipeline.
    Each instance gets isolated workspace for parallel trajectory generation.
    """

    environment_id = "enterprisebench"
    supports_isolated_instances = True

    def __init__(self, workspace_base: Optional[str] = None):
        """
        Initialize environment with workspace isolation.

        Args:
            workspace_base: Base directory for EnterpriseBench JSON files (unused by the
                isolation logic itself, which always uses a fresh OS temp dir; kept for
                interface parity with the training environment).
        """
        self.workspace_base = workspace_base or tempfile.gettempdir()
        self.source_root = Path(
            os.getenv("ENTERPRISEBENCH_ENV_ROOT", DEFAULT_ENTERPRISEBENCH_ENV_ROOT)
        ).resolve()
        self.path_alias_roots = [
            Path(alias).resolve()
            for alias in ENTERPRISEBENCH_PATH_ALIASES
            if Path(alias).exists()
        ]
        self.tools_instance = Tools()

        # Create isolated temp workspace for this trajectory
        self.temp_workspace = tempfile.mkdtemp(prefix="enterprise_eval_")
        logger.info(f"Created isolated workspace: {self.temp_workspace}")
        self.isolated_root = Path(self.temp_workspace) / "EnterpriseBench"
        shutil.copytree(self.source_root, self.isolated_root)
        logger.info("Copied EnterpriseBench environment to isolated root: %s", self.isolated_root)
        self._patch_tools_storage()

        # Map tool names to methods
        self.tool_methods = self._build_tool_map()

    def _patch_tools_storage(self) -> None:
        """Redirect all JSON reads/writes into the isolated EnterpriseBench copy."""

        def _load_json(path: str = "") -> List[Dict[str, Any]]:
            mapped_path = self._map_json_path(path)
            if not mapped_path:
                return []
            try:
                with open(mapped_path, "r", encoding="utf-8") as handle:
                    return json.load(handle)
            except (FileNotFoundError, json.JSONDecodeError):
                return []

        def _save_json(path: str, data: Any) -> None:
            mapped_path = self._map_json_path(path)
            if not mapped_path:
                return
            os.makedirs(os.path.dirname(mapped_path), exist_ok=True)
            with open(mapped_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)

        self.tools_instance.load_json = _load_json
        self.tools_instance.save_json = _save_json

    def _map_json_path(self, path: str = "") -> str:
        """Map any EnterpriseBench JSON path to the isolated trajectory copy."""
        if not path:
            return path

        original = Path(path)
        if not original.is_absolute():
            return str((self.isolated_root / original).resolve())

        for alias_root in self.path_alias_roots:
            try:
                relative = original.resolve().relative_to(alias_root)
                return str((self.isolated_root / relative).resolve())
            except ValueError:
                continue

        marker = "EnterpriseBench"
        parts = list(original.parts)
        if marker in parts:
            relative = Path(*parts[parts.index(marker) + 1 :])
            return str((self.isolated_root / relative).resolve())

        return str(original)

    def _build_tool_map(self) -> Dict[str, callable]:
        """Build mapping of tool names to callable methods."""
        # Get all methods from Tools class that are actual tools
        tool_map = {}

        # GitHub tools
        github_tools = [
            "github_list_my_repositories",
            "github_list_issues_of_repository",
            "github_create_repository",
            "github_create_issue",
            "github_get_issue",
            "github_update_repository",
            "github_delete_repository",
            "github_update_issue",
            "github_delete_issue",
            "github_get_repository_contents"
        ]

        # Email tools
        email_tools = [
            "read_email",
            "create_email",
            "update_email",
            "delete_email",
            "list_my_email_threads",
            "list_thread_ids_between_sender_recipient",
            "list_email_ids_in_thread"
        ]

        # Messaging/Collaboration tools
        collab_tools = [
            "send_message",
            "edit_message",
            "delete_message",
            "list_conversation_ids_between_employees",
            "fetch_conversation_by_id"
        ]

        # CRM - Customer Support
        crm_support_tools = [
            "read_customer_support_chat",
            "create_customer_support_chat",
            "update_customer_support_chat",
            "delete_customer_support_chat",
            "read_my_crm_chats",
            "list_customer_support_chats_by_product",
            "list_customer_support_chats_by_customer"
        ]

        # CRM - Products
        crm_product_tools = [
            "create_product",
            "get_product",
            "update_product",
            "delete_product",
            "list_products_by_category"
        ]

        # CRM - Customers
        crm_customer_tools = [
            "get_customer"
        ]

        # CRM - Product Sentiment/Reviews
        crm_sentiment_tools = [
            "create_product_sentiment",
            "get_product_reviews",
            "get_customer_reviews",
            "get_product_sentiment",
            "update_product_sentiment",
            "delete_product_sentiment"
        ]

        # CRM - Sales
        crm_sales_tools = [
            "create_sales_record",
            "get_sales_record",
            "update_sales_record",
            "delete_sales_record",
            "list_sales_by_product",
            "list_sales_by_customer",
            "list_sales_records_between_dates",
            "list_sales_records_by_customer_and_product"
        ]

        # IT Management Tools (New)
        it_tools = [
            "create_it_ticket",
            "get_it_ticket",
            "update_it_ticket",
            "delete_it_ticket",
            "assign_ticket",
            "resolve_ticket",
            "list_it_tickets_assigned_to_me",
            "get_it_ticket_ids_by_raiser",
            "list_it_tickets_by_priority"
        ]

        # Employee/HR Tools (New)
        employee_tools = [
            "create_employee_record",
            "fetch_employee_record",
            "update_employee_record",
            "deactivate_employee_record",
            "fetch_employees_by_ids",
            "get_emp_id_by_email"
        ]

        # Social Platform Tools (New)
        social_tools = [
            "enterprise_social_platform_create",
            "enterprise_social_platform_read",
            "enterprise_social_platform_update",
            "enterprise_social_platform_delete"
        ]

        # Inazuma Overflow Tools (New)
        inazuma_tools = [
            "inazuma_overflow_create",
            "inazuma_overflow_read",
            "inazuma_overflow_update",
            "inazuma_overflow_delete"
        ]

        all_tools = (
            github_tools + email_tools + collab_tools +
            crm_support_tools + crm_product_tools + crm_customer_tools +
            crm_sentiment_tools + crm_sales_tools +
            it_tools + employee_tools + social_tools + inazuma_tools
        )

        for tool_name in all_tools:
            if hasattr(self.tools_instance, tool_name):
                tool_map[tool_name] = getattr(self.tools_instance, tool_name)

        logger.info(f"Loaded {len(tool_map)} EnterpriseBench tools")
        return tool_map

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> ToolExecutionResult:
        """
        Execute a tool with given arguments.

        Args:
            tool_name: Name of the tool to execute
            arguments: Dictionary of arguments for the tool

        Returns:
            ToolExecutionResult with output or error
        """
        started_at = time.time()
        if tool_name not in self.tool_methods:
            return ToolExecutionResult(
                status=ToolExecutionStatus.TOOL_NOT_FOUND,
                output="",
                execution_time_ms=(time.time() - started_at) * 1000.0,
                error_message=(
                    f"Unknown tool: {tool_name}. "
                    f"Available tools: {list(self.tool_methods.keys())}"
                ),
            )

        try:
            # Call the tool method
            tool_method = self.tool_methods[tool_name]
            result = tool_method(arguments)

            # Convert result to string
            if isinstance(result, list):
                if len(result) == 0:
                    output = "No results found."
                else:
                    # Format as readable JSON
                    import json
                    output = json.dumps(result, indent=2)
            else:
                output = str(result)

            return ToolExecutionResult(
                status=ToolExecutionStatus.SUCCESS,
                output=output,
                execution_time_ms=(time.time() - started_at) * 1000.0,
                error_message=None,
            )

        except Exception as e:
            logger.error(f"Error executing {tool_name}: {e}", exc_info=True)
            return ToolExecutionResult(
                status=ToolExecutionStatus.RUNTIME_ERROR,
                output="",
                execution_time_ms=(time.time() - started_at) * 1000.0,
                error_message=f"Tool execution failed: {str(e)}",
            )

    def state_fingerprint(self) -> str:
        """Hash mutable JSON state in this trajectory's isolated workspace."""
        digest = hashlib.sha256()
        for path in sorted(self.isolated_root.rglob("*.json")):
            relative = path.relative_to(self.isolated_root)
            relative_text = relative.as_posix()
            if (
                "Task_Generation" in relative.parts
                or relative.name in {
                    "training_tasks.json",
                    "new_training_tasks.json",
                    "selected_training_tasks_2000.json",
                    "tasks.json",
                }
            ):
                continue
            digest.update(relative_text.encode("utf-8"))
            try:
                digest.update(path.read_bytes())
            except OSError:
                digest.update(b"<unreadable>")
        return digest.hexdigest()

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Get tool schemas for all available tools in list format.

        Returns:
            List of tool dictionaries with 'name', 'description', and 'args_schema' fields
        """
        tool_schema = self.get_tool_schema()
        tools_list = []

        for tool_name, schema in tool_schema.items():
            tools_list.append({
                "name": tool_name,
                "description": schema.get("description", ""),
                "args_schema": schema.get("args_schema", {})
            })

        return tools_list

    def reset(self):
        """Clean up workspace after trajectory generation."""
        try:
            if hasattr(self, 'temp_workspace'):
                shutil.rmtree(self.temp_workspace, ignore_errors=True)
                logger.debug(f"Cleaned up workspace: {self.temp_workspace}")
        except Exception as e:
            logger.warning(f"Failed to clean workspace: {e}")

    @staticmethod
    def get_tool_schema() -> Dict[str, Dict[str, Any]]:
        """
        Get complete tool schema for prompt generation.

        Returns all EnterpriseBench tools with descriptions and argument schemas.
        """
        schema_path = Path(os.getenv("ENTERPRISE_TOOLS_SCHEMA_PATH", str(ENTERPRISEBENCH_TOOLS_JSON_PATH)))
        with schema_path.open("r", encoding="utf-8") as handle:
            tool_entries = json.load(handle)

        schema: Dict[str, Dict[str, Any]] = {}
        for entry in tool_entries:
            name = str(entry.get("name", "")).strip()
            if not name:
                continue
            schema[name] = {
                "description": entry.get("description", ""),
                "args_schema": entry.get("args_schema", {}) or {},
            }
        return schema


def create_enterprise_tool_environment():
    """Factory function for creating isolated environments."""
    return EnterpriseBenchToolEnvironment()
