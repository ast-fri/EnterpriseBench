#!/usr/bin/env python3
"""
Task Runner Script
Executes all task generation commands sequentially with progress tracking and error handling.
"""

import sys
import subprocess
import time
from datetime import datetime
import logging
from pathlib import Path

# Add current directory to path
sys.path.append('.')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('task_runner.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

COMMANDS = {   
    # ===== ANALYSIS TASKS =====
    # "github_analysis": (
    #     "python -m Task_Generation_sft_batch2_copy.generators.search_generator --config Task_Generation_sft_batch2_copy/Config/SWE/config_github_analysis.json --task_domain swe  --task_category github --output Task_Generation_sft_batch2_copy/generated_tasks_2/SWE/Github_Analysis/github_analysis"
    # ),
    # "swe_conv_analysis": (
    #     "python -m Task_Generation_sft_batch2_copy.generators.search_generator --config Task_Generation_sft_batch2_copy/Config/SWE/config_conv_read.json --task_domain swe --task_category conv --output Task_Generation_sft_batch2_copy/generated_tasks_2/SWE/Conversation/Read/swe_conv_analysis"
    # ),
    # "hr_conv_analysis": (
    #     "python -m Task_Generation_sft_batch2_copy.generators.search_generator --config Task_Generation_sft_batch2_copy/Config/HR_System/config_conv_read.json --task_domain hr --task_category conv --output Task_Generation_sft_batch2_copy/generated_tasks_2/HR_System/Conversation/Read/hr_conv_analysis"
    # ),
    # "hr_employee_analysis": (
    #     "python -m Task_Generation_sft_batch2_copy.generators.search_generator --config Task_Generation_sft_batch2_copy/Config/HR_System/config_employee_analysis.json --task_domain hr --task_category employee --output Task_Generation_sft_batch2_copy/generated_tasks_2/HR_System/Employee_Database_Management/Analysis/employee_analysis"
    # ),
    # "sales_conv_analysis": (
    #     "python -m Task_Generation_sft_batch2_copy.generators.search_generator --config Task_Generation_sft_batch2_copy/Config/Sales/config_conv_read.json --task_domain sales --task_category conv --output Task_Generation_sft_batch2_copy/generated_tasks_2/Sales/Conversation/Read/sales_conv_analysis"
    # ),
    # "it_conv_analysis": (
    #     "python -m Task_Generation_sft_batch2_copy.generators.search_generator --config Task_Generation_sft_batch2_copy/Config/IT_Solutions/config_conv_read.json --task_domain it --task_category conv --output Task_Generation_sft_batch2_copy/generated_tasks_2/IT_Solutions/Conversation/Read/it_conv_analysis"
    # ),
    # "it_ticket_analysis": (
    #     "python -m Task_Generation_sft_batch2_copy.generators.search_generator --config Task_Generation_sft_batch2_copy/Config/IT_Solutions/config_ticket_analysis.json --task_domain it --task_category tickets --output Task_Generation_sft_batch2_copy/generated_tasks_2/IT_Solutions/Ticket_Database_Management/Analysis/it_ticket_analysis"
    # ),
    # "manag_conv_analysis": (
    #     "python -m Task_Generation_sft_batch2_copy.generators.search_generator --config Task_Generation_sft_batch2_copy/Config/Business_Operations_Management/config_conv_read.json --task_domain manag --task_category conv --output Task_Generation_sft_batch2_copy/generated_tasks_2/Business_Operations_Management/Conversation/Read/management_conv_analysis"
    # ),

    # # ===== CRM ANALYSIS =====
    # "Product Task": (
    #     "python -m Task_Generation_sft_batch2_copy.generators.search_generator --config Task_Generation_sft_batch2_copy/Config/Sales/config_product_analysis.json --task_domain sales --task_category products --output Task_Generation_sft_batch2_copy/generated_tasks_2/Sales/Sales_Database_Management/product_task/Analysis/product_analysis_task"
    # ),
    # "Customer Task": (
    #     "python -m Task_Generation_sft_batch2_copy.generators.search_generator --config Task_Generation_sft_batch2_copy/Config/Sales/config_customer_analysis.json --task_domain sales --task_category customer  --output Task_Generation_sft_batch2_copy/generated_tasks_2/Sales/Sales_Database_Management/customer_task/Analysis/customer_analysis_task"
    # ),
    # "Support Rep Task": (
    #     """python -m Task_Generation_sft_batch2_copy.generators.search_generator --config Task_Generation_sft_batch2_copy/Config/Sales/config_support_rep_analysis.json --task_domain sales --task_category support --output Task_Generation_sft_batch2_copy/generated_tasks_2/Sales/Sales_Database_Management/support_task/Analysis/support_rep_analysis_task"""
    # ),

    # # ===== CONVERSATION GENERATION =====
    # HR
    # "Email HR": (
    #     """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain hr --task_category conv  --config Task_Generation_sft_batch2_copy/Config/HR_System/config_conv_email.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/HR_System/Conversation/Create/email"""
    # ),
    # "Message HR": (
    #     """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain hr --task_category conv  --config Task_Generation_sft_batch2_copy/Config/HR_System/config_conv_message.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/HR_System/Conversation/Create/message"""
    # ),
    # # IT
    # "Email IT": (
    #     """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain it --task_category conv --config Task_Generation_sft_batch2_copy/Config/IT_Solutions/config_conv_email.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/IT_Solutions/Conversation/Create/email"""
    # ),
    # "Message IT": (
    #     """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain it --task_category conv --config Task_Generation_sft_batch2_copy/Config/IT_Solutions/config_conv_message.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/IT_Solutions/Conversation/Create/message"""
    # ),
    # # Sales
    # "Email Sales": (
    #     """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain sales --task_category conv --config Task_Generation_sft_batch2_copy/Config/Sales/config_conv_email.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/Sales/Conversation/Create/email"""
    # ),
    # "Message Sales": (
    #     """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain sales --task_category conv --config Task_Generation_sft_batch2_copy/Config/Sales/config_conv_message.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/Sales/Conversation/Create/message"""
    # ),
    # # SWE
    # "Email SWE": (
    #     """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain swe --task_category conv --config Task_Generation_sft_batch2_copy/Config/SWE/config_conv_email.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/SWE/Conversation/Create/email"""
    # ),
    # "Message SWE": (
    #     """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain swe --task_category conv --config Task_Generation_sft_batch2_copy/Config/SWE/config_conv_message.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/SWE/Conversation/Create/message"""
    # ),
    # Management
    "Email Manage": (
        """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain manag --task_category conv --config Task_Generation_sft_batch2_copy/Config/Business_Operations_Management/config_conv_email.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/Business_Operations_Management/Conversation/Create/email"""
    ),
    "Message Manage": (
        """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain manag --task_category conv --config Task_Generation_sft_batch2_copy/Config/Business_Operations_Management/config_conv_message.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/Business_Operations_Management/Conversation/Create/message"""
    ),

    # # ===== CRUD and PATCHER TASKS =====
    "CRUD_github": (
        """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain swe --task_category github  --config Task_Generation_sft_batch2_copy/Config/SWE/config_crud_github.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/SWE/Workspace_Database_Management/github_crud"""
    ),
    "CRUD_product": (
        """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain sales --task_category products --config Task_Generation_sft_batch2_copy/Config/Sales/config_crud_products.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/Sales/Sales_Database_Management/product_task/CRUD/product_crud"""
    ),
    "CRUD_sales": (
        """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain sales --task_category customers --config Task_Generation_sft_batch2_copy/Config/Sales/config_crud_sales.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/Sales/Sales_Database_Management/customer_task/CRUD/sales_crud"""
    ),
    "CRUD_customers": (
        """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain sales --task_category customers --config Task_Generation_sft_batch2_copy/Config/Sales/config_crud_customers.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/Sales/Sales_Database_Management/customer_task/CRUD/customers_crud"""
    ),
    "CRUD_support": (
        """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain sales --task_category support --config Task_Generation_sft_batch2_copy/Config/Sales/config_crud_support.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/Sales/Sales_Database_Management/support_task/CRUD/support_crud"""
    ),
    
    "CRUD_it": (
        """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain it --task_category tickets --config Task_Generation_sft_batch2_copy/Config/IT_Solutions/config_crud_tickets.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/IT_Solutions/Ticket_Database_Management/CRUD/tickets_crud"""
    ),
    "CRUD_employee": (
        """python -m Task_Generation_sft_batch2_copy.generators.search_generator --task_domain hr --task_category employees --config Task_Generation_sft_batch2_copy/Config/HR_System/config_crud_employees.json --output Task_Generation_sft_batch2_copy/generated_tasks_2/HR_System/Employee_Database_Management/CRUD/employees_crud"""
    ),
    # "code_issue_patcher_task": (
    #     """python -m Task_Generation_sft_batch2_copy.generators.swe_generator --config Task_Generation_sft_batch2_copy/Config/SWE/config_code_patch.json --task_category github_ids --task_domain swe --task_class github --output Task_Generation_sft_batch2_copy/generated_tasks_2/SWE/Code_Issue_Patcher/code_patch"""
    # )
}


def run_command(name, command, timeout=3600):
    """
    Execute a single command with timeout and error handling.
    
    Args:
        name: Name of the task
        command: Command string to execute
        timeout: Timeout in seconds (default: 1 hour)
    
    Returns:
        tuple: (success: bool, execution_time: float, error_message: str)
    """
    logger.info(f"Starting task: {name}")
    logger.info(f"Command: {command}")
    
    start_time = time.time()
    
    try:
        # Create output directories if they don't exist
        if '--output' in command or '--output' in command:
            # Extract output directory from command
            parts = command.split()
            for i, part in enumerate(parts):
                if part in ['--output', '--output'] and i + 1 < len(parts):
                    output_dir = Path(parts[i + 1])
                    output_dir.parent.mkdir(parents=True, exist_ok=True)
                    break
        
        # Execute the command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd='.'
        )
        
        execution_time = time.time() - start_time
        
        if result.returncode == 0:
            logger.info(f"✅ Task '{name}' completed successfully in {execution_time:.2f}s")
            if result.stdout:
                logger.info(f"Output: {result.stdout[:500]}...")
            return True, execution_time, ""
        else:
            logger.error(f"❌ Task '{name}' failed with return code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            return False, execution_time, result.stderr
            
    except subprocess.TimeoutExpired:
        execution_time = time.time() - start_time
        logger.error(f"⏰ Task '{name}' timed out after {timeout}s")
        return False, execution_time, f"Command timed out after {timeout} seconds"
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"💥 Task '{name}' failed with exception: {str(e)}")
        return False, execution_time, str(e)


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("TASK RUNNER STARTING")
    logger.info(f"Total tasks to execute: {len(COMMANDS)}")
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    # Statistics tracking
    total_tasks = len(COMMANDS)
    successful_tasks = 0
    failed_tasks = 0
    total_execution_time = 0
    failed_task_details = []
    
    overall_start_time = time.time()
    
    # Execute each command
    for i, (task_name, command) in enumerate(COMMANDS.items(), 1):
        logger.info(f"\n[{i}/{total_tasks}] Executing: {task_name}")
        logger.info("-" * 60)
        
        success, exec_time, error_msg = run_command(task_name, command)
        total_execution_time += exec_time
        
        if success:
            successful_tasks += 1
        else:
            failed_tasks += 1
            failed_task_details.append({
                'name': task_name,
                'error': error_msg,
                'execution_time': exec_time
            })
    
    # Final summary
    overall_execution_time = time.time() - overall_start_time
    
    logger.info("\n" + "=" * 80)
    logger.info("TASK RUNNER COMPLETED")
    logger.info("=" * 80)
    logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Total execution time: {overall_execution_time:.2f}s ({overall_execution_time/60:.1f} minutes)")
    logger.info(f"Total tasks: {total_tasks}")
    logger.info(f"✅ Successful: {successful_tasks}")
    logger.info(f"❌ Failed: {failed_tasks}")
    logger.info(f"Success rate: {(successful_tasks/total_tasks)*100:.1f}%")
    
    if failed_tasks > 0:
        logger.info("\nFAILED TASKS SUMMARY:")
        logger.info("-" * 40)
        for task in failed_task_details:
            logger.info(f"• {task['name']} (took {task['execution_time']:.2f}s)")
            logger.info(f"  Error: {task['error'][:200]}...")
    
    # Exit with appropriate code
    sys.exit(0 if failed_tasks == 0 else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Task runner interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {str(e)}")
        sys.exit(1)
    