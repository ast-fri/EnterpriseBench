import streamlit as st
import subprocess
import os
import json
import sys
import glob
from pathlib import Path

# Set page configuration
st.set_page_config(
    page_title="Enterprise Task Generator",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import the COMMANDS dictionary from the run_task.py file
sys.path.append('.')
COMMANDS = {   
        # ===== ANALYSIS TASKS =====
    "github_analysis": (
            "python -m Task_Generation_sft_batch2.generators.analysis_generator   --config Task_Generation_sft_batch2/Config/SWE/config_github_analysis.json --task_domain swe --task_category github_ids --task_class github --output Task_Generation_sft_batch2/generated_tasks/SWE/Github_Analysis/github_analysis"
        ),
        "swe_conv_analysis": (
            "python -m Task_Generation_sft_batch2.generators.analysis_generator   --config Task_Generation_sft_batch2/Config/SWE/config_conv_read.json --task_domain swe --task_category swe --task_class conv --output Task_Generation_sft_batch2/generated_tasks/SWE/Conversation/Read/swe_conv_analysis"
        ),
        "hr_conv_analysis": (
            "python -m Task_Generation_sft_batch2.generators.analysis_generator   --config Task_Generation_sft_batch2/Config/HR_System/config_conv_read.json --task_domain hr --task_category hr --task_class conv --output Task_Generation_sft_batch2/generated_tasks/HR_System/Conversation/Read/hr_conv_analysis"
        ),
        "hr_employee_analysis": (
            "python -m Task_Generation_sft_batch2.generators.analysis_generator   --config Task_Generation_sft_batch2/Config/HR_System/config_employee_analysis.json --task_domain hr --task_category emp --task_class employee --output Task_Generation_sft_batch2/generated_tasks/HR_System/Employee_Database_Management/Analysis/employee_analysis"
        ),
        # "hr_policy_analysis": (
        #     "python -m Task_Generation_sft_batch2.generators.analysis_generator   --config Task_Generation_sft_batch2/Config/HR_System/config_policy_analysis.json  --output Task_Generation_sft_batch2/generated_tasks/HR_System/Policy_Documents_Management/Read/policy_doc_analysis"
        # ),
        "sales_conv_analysis": (
            "python -m Task_Generation_sft_batch2.generators.analysis_generator   --config Task_Generation_sft_batch2/Config/Sales/config_conv_read.json --task_domain sales --task_category sales --task_class conv --output Task_Generation_sft_batch2/generated_tasks/Sales/Conversation/Read/sales_conv_analysis"
        ),
        "it_conv_analysis": (
            "python -m Task_Generation_sft_batch2.generators.analysis_generator   --config Task_Generation_sft_batch2/Config/IT_Solutions/config_conv_read.json --task_domain it --task_category engg --task_class conv --output Task_Generation_sft_batch2/generated_tasks/IT_Solutions/Conversation/Read/it_conv_analysis"
        ),
        "it_ticket_analysis": (
            "python -m Task_Generation_sft_batch2.generators.analysis_generator   --config Task_Generation_sft_batch2/Config/IT_Solutions/config_ticket_analysis.json --task_domain it --task_category tickets --task_class tickets --output Task_Generation_sft_batch2/generated_tasks/IT_Solutions/Ticket_Database_Management/Analysis/it_ticket_analysis"
        ),
        "manag_conv_analysis": (
            "python -m Task_Generation_sft_batch2.generators.analysis_generator   --config Task_Generation_sft_batch2/Config/Business_Operations_Management/config_conv_read.json --task_domain manag --task_category manag --task_class conv --output Task_Generation_sft_batch2/generated_tasks/Business_Operations_Management/Conversation/Read/management_conv_analysis"
        ),

    # ===== CRM ANALYSIS =====
        "Product Task": (
            "python -m Task_Generation_sft_batch2.generators.crm_generator --config Task_Generation_sft_batch2/Config/Sales/config_product_analysis.json --task-type product_sales --task_domain sales --task_category Products --task_class product --output Task_Generation_sft_batch2/generated_tasks/Sales/Sales_Database_Management/product_task/Analysis/product_analysis_task"
        ),
        "Customer Task": (
            "python -m Task_Generation_sft_batch2.generators.crm_generator --config Task_Generation_sft_batch2/Config/Sales/config_customer_analysis.json --task-type customer_sentiment --task_domain sales --task_category Customers --task_class customer --output Task_Generation_sft_batch2/generated_tasks/Sales/Sales_Database_Management/customer_task/Analysis/customer_analysis_task"
        ),
        "Support Rep Task": (
            "python -m Task_Generation_sft_batch2.generators.crm_generator --config Task_Generation_sft_batch2/Config/Sales/config_support_rep_analysis.json --task-type support_rep --task_domain sales --task_category Support --task_class support --output Task_Generation_sft_batch2/generated_tasks/Sales/Sales_Database_Management/support_task/Analysis/support_rep_analysis_task"
        ),
        # ===== CONVERSATION GENERATION =====
        # HR
        "Email HR": (
            """python -m Task_Generation_sft_batch2.generators.conv_generator --task_category \"Enterprise Mail System\" --conv_source \"HR Conversations\" --id_type emp_id --config_file Task_Generation_sft_batch2/Config/HR_System/config_conv_email.json --target_dir Task_Generation_sft_batch2/generated_tasks/HR_System/Conversation/Create/email"""
        ),
        "Message HR": (
            "python -m Task_Generation_sft_batch2.generators.conv_generator "
            "--task_category \"HR Conversations\" "
            "--conv_source \"HR Conversations\" "
            "--id_type emp_id "
            "--config_file Task_Generation_sft_batch2/Config/HR_System/config_conv_message.json "
            "--target_dir Task_Generation_sft_batch2/generated_tasks/HR_System/Conversation/Create/message"
        ),
        # IT
        "Email IT": (
            "python -m Task_Generation_sft_batch2.generators.conv_generator "
            "--task_category \"Enterprise Mail System\" "
            "--conv_source \"Engineering Team Conversations\" "
            "--id_type emp_id "
            "--config_file Task_Generation_sft_batch2/Config/IT_Solutions/config_conv_email.json "
            "--target_dir Task_Generation_sft_batch2/generated_tasks/IT_Solutions/Conversation/Create/email"
        ),
        "Message IT": (
            "python -m Task_Generation_sft_batch2.generators.conv_generator "
            "--task_category \"Engineering Team Conversations\" "
            "--conv_source \"Engineering Team Conversations\" "
            "--id_type emp_id "
            "--config_file Task_Generation_sft_batch2/Config/IT_Solutions/config_conv_message.json "
            "--target_dir Task_Generation_sft_batch2/generated_tasks/IT_Solutions/Conversation/Create/message"
        ),
        # Sales
        "Email Sales": (
            "python -m Task_Generation_sft_batch2.generators.conv_generator "
            "--task_category \"Enterprise Mail System\" "
            "--conv_source \"Sales Team Conversations\" "
            "--id_type emp_id "
            "--config_file Task_Generation_sft_batch2/Config/Sales/config_conv_email.json "
            "--target_dir Task_Generation_sft_batch2/generated_tasks/Sales/Conversation/Create/email"
        ),
        "Message Sales": (
            "python -m Task_Generation_sft_batch2.generators.conv_generator "
            "--task_category \"Sales Team Conversations\" "
            "--conv_source \"Sales Team Conversations\" "
            "--id_type emp_id "
            "--config_file Task_Generation_sft_batch2/Config/Sales/config_conv_message.json "
            "--target_dir Task_Generation_sft_batch2/generated_tasks/Sales/Conversation/Create/message"
        ),
        # SWE
        "Email SWE": (
            "python -m Task_Generation_sft_batch2.generators.conv_generator "
            "--task_category \"Enterprise Mail System\" "
            "--conv_source \"SDE Conversations\" "
            "--id_type emp_id "
            "--config_file Task_Generation_sft_batch2/Config/SWE/config_conv_email.json "
            "--target_dir Task_Generation_sft_batch2/generated_tasks/SWE/Conversation/Create/email"
        ),
        "Message SWE": (
            "python -m Task_Generation_sft_batch2.generators.conv_generator "
            "--task_category \"SDE Conversations\" "
            "--conv_source \"SDE Conversations\" "
            "--id_type emp_id "
            "--config_file Task_Generation_sft_batch2/Config/SWE/config_conv_message.json "
            "--target_dir Task_Generation_sft_batch2/generated_tasks/SWE/Conversation/Create/message"
        ),
        # Management
        "Email Manage": (
            "python -m Task_Generation_sft_batch2.generators.conv_generator "
            "--task_category \"Enterprise Mail System\" "
            "--conv_source \"Management Team Conversations\" "
            "--id_type emp_id "
            "--config_file Task_Generation_sft_batch2/Config/Business_Operations_Management/config_conv_email.json "
            "--target_dir Task_Generation_sft_batch2/generated_tasks/Business_Operations_Management/Conversation/Create/email"
        ),
        "Message Manage": (
            "python -m Task_Generation_sft_batch2.generators.conv_generator "
            "--task_category \"Management Team Conversations\" "
            "--conv_source \"Management Team Conversations\" "
            "--id_type emp_id "
            "--config_file Task_Generation_sft_batch2/Config/Business_Operations_Management/config_conv_message.json "
            "--target_dir Task_Generation_sft_batch2/generated_tasks/Business_Operations_Management/Conversation/Create/message"
        ),

        # ===== CRM ANALYSIS =====
        "Product Task": (
            "python -m Task_Generation_sft_batch2.generators.crm_generator --config Task_Generation_sft_batch2/Config/Sales/config_product_analysis.json --task-type product_sales --task_domain sales --task_category Products --task_class product --output Task_Generation_sft_batch2/generated_tasks/Sales/Sales_Database_Management/product_task/Analysis/product_analysis_task"
        ),
        "Customer Task": (
            "python -m Task_Generation_sft_batch2.generators.crm_generator --config Task_Generation_sft_batch2/Config/Sales/config_customer_analysis.json --task-type customer_sentiment --task_domain sales --task_category Customers --task_class customer --output Task_Generation_sft_batch2/generated_tasks/Sales/Sales_Database_Management/customer_task/Analysis/customer_analysis_task"
        ),
        "Support Rep Task": (
            "python -m Task_Generation_sft_batch2.generators.crm_generator --config Task_Generation_sft_batch2/Config/Sales/config_support_rep_analysis.json --task-type support_rep --task_domain sales --task_category Support --task_class support --output Task_Generation_sft_batch2/generated_tasks/Sales/Sales_Database_Management/support_task/Analysis/support_rep_analysis_task"
        ),

    

    # ===== CRUD and PATCHER TASKS =====
        "CRUD_github": (
            "python -m Task_Generation_sft_batch2.generators.crud_generator --config Task_Generation_sft_batch2/Config/SWE/config_crud_github.json --task_domain swe --id_type emp_id --target_dir Task_Generation_sft_batch2/generated_tasks/SWE/Workspace_Database_Management/github_crud"
        ),
    "CRUD_product": (
        "python -m Task_Generation_sft_batch2.generators.crud_generator --config Task_Generation_sft_batch2/Config/Sales/config_crud_product.json --task_domain product --id_type product_id --target_dir Task_Generation_sft_batch2/generated_tasks/Sales/Sales_Database_Management/product_task/CRUD/product_crud"
    ),
    "CRUD_sales": (
        "python -m Task_Generation_sft_batch2.generators.crud_generator --config Task_Generation_sft_batch2/Config/Sales/config_crud_sales.json --task_domain product --id_type product_id --target_dir Task_Generation_sft_batch2/generated_tasks/Sales/Sales_Database_Management/customer_task/CRUD/sales_crud"
    ),
    "CRUD_it": (
        "python -m Task_Generation_sft_batch2.generators.crud_generator --config Task_Generation_sft_batch2/Config/IT_Solutions/config_crud_tickets.json --task_domain tickets --id_type id --target_dir Task_Generation_sft_batch2/generated_tasks/IT_Solutions/Ticket_Database_Management/CRUD/tickets_crud"
    ),
    "CRUD_employee": (
        "python -m Task_Generation_sft_batch2.generators.crud_generator --config Task_Generation_sft_batch2/Config/HR_System/config_crud_employees.json --task_domain emp --id_type emp_id --target_dir Task_Generation_sft_batch2/generated_tasks/HR_System/Employee_Database_Management/CRUD/employees_crud"
    ),
    
    "code_issue_patcher_task": (
        "python -m Task_Generation_sft_batch2.generators.swe_generator --config Task_Generation_sft_batch2/Config/SWE/config_code_patch.json --task_domain github_ids --output Task_Generation_sft_batch2/generated_tasks/SWE/Code_Issue_Patcher/code_patch"
    )
}

# Add custom CSS
def apply_custom_css():
    st.markdown("""
    <style>
        /* Main container styling */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* Title and headers */
        h1 {
            color: #2c3e50;
            font-size: 2.5rem !important;
            font-weight: 700 !important;
            margin-bottom: 1.5rem !important;
            text-align: center;
            padding-bottom: 1rem;
            border-bottom: 2px solid #3498db;
        }
        
        h2, h3, .subheader {
            color: #3498db;
            font-weight: 600 !important;
            margin-top: 1.5rem !important;
        }
        
        /* Sidebar styling */
        .css-1d391kg, .css-1v3fvcr {
            background-color: #f8f9fa;
        }
        
        .sidebar .sidebar-content {
            background-color: #f8f9fa;
        }
        
        /* Button styling */
        .stButton > button {
            background-color: #3498db;
            color: white;
            font-weight: 500;
            border-radius: 6px;
            padding: 0.5rem 1rem;
            border: none;
            width: 100%;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            background-color: #2980b9;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            transform: translateY(-2px);
        }
        
        /* Slider and selectbox styling */
        .stSlider, .stSelectbox {
            padding: 0.5rem 0;
        }
        
        /* Code blocks */
        .stCodeBlock {
            border-radius: 6px;
            border: 1px solid #e0e0e0;
            margin: 1rem 0;
        }
        
        /* Card-like panels for content */
        .card {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }
        
        /* Status indicators */
        .success-box {
            background-color: #d4edda;
            color: #155724;
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
            border-left: 5px solid #28a745;
        }
        
        .error-box {
            background-color: #f8d7da;
            color: #721c24;
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
            border-left: 5px solid #dc3545;
        }
        
        /* Checkboxes */
        .stCheckbox > label > span {
            font-weight: 500;
        }
        
        /* Department icons */
        .dept-icon {
            font-size: 1.2rem;
            margin-right: 8px;
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            font-weight: 600;
            color: #2c3e50;
        }
        
        /* JSON display enhancements */
        pre {
            background-color: #f8f9fa;
            border-radius: 6px;
            padding: 1rem;
            white-space: pre-wrap;
        }
        
        /* Terminal output */
        .terminal {
            background-color: #1e1e1e;
            color: #f8f8f8;
            font-family: monospace;
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
            max-height: 400px;
            overflow-y: auto;
        }
        
        /* Task selection indicators */
        .task-selected {
            border-left: 4px solid #3498db;
            padding-left: 10px;
        }
        
        /* Command display */
        .command-display {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
            margin: 1rem 0;
            font-family: monospace;
        }
    </style>
    """, unsafe_allow_html=True)

# Department icons dictionary
department_icons = {
    "HR": "👥",
    "Software Engineering": "💻",
    "IT Solutions": "🔧",
    "Sales": "📊",
    "Business Operations Management": "📈"
}

# Category icons dictionary
category_icons = {
    "Search": "🔍",
    "Communication": "✉️",
    "Database Management": "🗄️",
    "Code Management": "📝",
    "CRM Tasks": "👥"
}

def run_command(task_key, n_tasks, terminal):
    """Run the selected command and return the status"""
    if task_key not in COMMANDS:
        return False, f"Error: No command found for '{task_key}'"
    
    try:
        command = COMMANDS[task_key]
        # Add the --n parameter with the selected number of tasks
        command = f"{command} --n {n_tasks}"
        
        # Create placeholder for real-time output
        output_placeholder = st.empty()
        terminal_output = ""
        
        # Use Popen to get real-time output
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        if terminal:
            # Create a terminal-like container
            with output_placeholder.container():
                terminal_container = st.empty()
                
                # Read and display output in real-time
                for line in iter(process.stdout.readline, ''):
                    if not line:
                        break
                    terminal_output += line
                    # Update the container with all accumulated output with terminal styling
                    terminal_container.markdown("""
                    <div class="terminal">
                    """ + terminal_output.replace('\n', '<br>') + """
                    </div>
                    """, unsafe_allow_html=True)
        
        # Get return code
        return_code = process.wait()
        
        if return_code == 0:
            return True, terminal_output
        else:
            return False, f"Command failed with return code {return_code}\n{terminal_output}"
    except Exception as e:
        return False, f"Exception occurred: {str(e)}"

def extract_output_path(command_string):
    """Extract the output file path from the command string"""
    parts = command_string.split()
    output_index = -1
    
    try:
        output_index = parts.index("--output")
    except ValueError:
        return None
    
    if output_index + 1 < len(parts):
        return parts[output_index + 1]
    return None

def display_output_file(output_path):
    """Display the content of the output file or files in the directory"""
    if not output_path:
        return "Could not determine output path"
    
    # Check if the path is a file or directory
    path = Path(output_path)
    
    # If it's a .json file, display it directly
    if path.suffix == '.json' and path.exists():
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                return data
        except Exception as e:
            return f"Error reading output file: {str(e)}"
    
    # If it's a directory, look for json files
    if path.is_dir():
        json_files = list(path.glob('*.json'))
        if json_files:
            try:
                with open(json_files[0], 'r') as f:
                    data = json.load(f)
                    if len(json_files) > 1:
                        st.info(f"Found {len(json_files)} files. Showing the first one: {json_files[0].name}")
                    return data
            except Exception as e:
                return f"Error reading output file: {str(e)}"
        else:
            return f"No .json files found in {output_path}"
    
    # If path doesn't exist, try adding .json extension
    json_path = Path(f"{output_path}.json")
    if json_path.exists():
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
                return data
        except Exception as e:
            return f"Error reading output file: {str(e)}"
    
    # Try finding any json files that start with the output path
    parent_dir = path.parent
    if parent_dir.exists():
        pattern = f"{path.name}*.json"
        matching_files = list(parent_dir.glob(pattern))
        if matching_files:
            try:
                with open(matching_files[0], 'r') as f:
                    data = json.load(f)
                    if len(matching_files) > 1:
                        st.info(f"Found {len(matching_files)} files. Showing the first one: {matching_files[0].name}")
                    return data
            except Exception as e:
                return f"Error reading output file: {str(e)}"
    
    return f"Could not find output file at {output_path}"

def main():
    # Apply custom CSS
    apply_custom_css()
    
    # App header with logo effect
    st.markdown("""
    <div style="text-align: center;">
        <span style="font-size: 3rem; color: #3498db;">🚀</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.title("Enterprise Task Generator")
    
    # Brief description
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        Generate enterprise tasks for different departments and use cases.
        Select options from the sidebar to customize your task generation.
    </div>
    """, unsafe_allow_html=True)
    
    # Map user-friendly names to task keys
    task_display_map = {
        # HR tasks
        "HR Conversation Search": "hr_conv_analysis",
        "Employee Database Search": "hr_employee_analysis",
        "Policy Documents Search": "hr_policy_analysis",
        "HR Email Creation": "Email HR",
        "HR Message Creation": "Message HR",
        "Employee Database Management": "CRUD_employee",
        
        # Software Engineering tasks
        "GitHub Repository Search": "github_analysis",
        "SWE Conversation Search": "swe_conv_analysis",
        "SWE Email Creation": "Email SWE",
        "SWE Message Creation": "Message SWE",
        "GitHub Database Management": "CRUD_github",
        "Code Issue Patching": "code_issue_patcher_task",
        
        # IT Solutions tasks
        "IT Conversation Search": "it_conv_analysis",
        "IT Ticket Search": "it_ticket_analysis",
        "IT Email Creation": "Email IT",
        "IT Message Creation": "Message IT",
        "Ticket Database Management": "CRUD_it",
        
        # Sales tasks
        "Sales Conversation Search": "sales_conv_analysis",
        "Sales Email Creation": "Email Sales",
        "Sales Message Creation": "Message Sales",
        "Product Database Management": "CRUD_product",
        "Sales Database Management": "CRUD_sales",
        "Product Sales Search": "Product Task",
        "Customer Sentiment Search": "Customer Task",
        "Support Rep Performance Search": "Support Rep Task",
        
        # Business Operations Management tasks
        "Management Conversation Search": "manag_conv_analysis",
        "Management Email Creation": "Email Manage",
        "Management Message Creation": "Message Manage"
    }
    
    # Reverse mapping for lookup
    task_key_map = {v: k for k, v in task_display_map.items()}
    
    # Organize tasks by department with display names
    departments = {
        "HR": {
            "Search": ["HR Conversation Search", "Employee Database Search", "Policy Documents Search"],
            "Communication": ["HR Email Creation", "HR Message Creation"],
            "Database Management": ["Employee Database Management"]
        },
        "Software Engineering": {
            "Search": ["GitHub Repository Search", "SWE Conversation Search"],
            "Communication": ["SWE Email Creation", "SWE Message Creation"],
            "Database Management": ["GitHub Database Management"],
            "Code Management": ["Code Issue Patching"]
        },
        "IT Solutions": {
            "Search": ["IT Conversation Search", "IT Ticket Search"],
            "Communication": ["IT Email Creation", "IT Message Creation"],
            "Database Management": ["Ticket Database Management"]
        },
        "Sales": {
            "Search": ["Sales Conversation Search"],
            "Communication": ["Sales Email Creation", "Sales Message Creation"],
            "Database Management": ["Product Database Management", "Sales Database Management"],
            "CRM Tasks": ["Product Sales Search", "Customer Sentiment Search", "Support Rep Performance Search"]
        },
        "Business Operations Management": {
            "Search": ["Management Conversation Search"],
            "Communication": ["Management Email Creation", "Management Message Creation"]
        }
    }
    
    # Create sidebar for department selection
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 1rem 0;">
        <h3 style="color: #3498db;">Configure Task Generation</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Department selection with icons
    st.sidebar.markdown("### Department Selection")
    dept_options = list(departments.keys())
    dept_options_with_icons = [f"{department_icons[dept]} {dept}" for dept in dept_options]
    
    selected_dept_with_icon = st.sidebar.selectbox(
        "Select Department",
        options=dept_options_with_icons,
        index=0,
        help="Choose a department to view available tasks"
    )
    
    # Extract department name without icon
    selected_department = selected_dept_with_icon.split(" ", 1)[1]
    
    # Display categories for the selected department with icons
    st.sidebar.markdown("### Task Categories")
    category_options = list(departments[selected_department].keys())
    category_options_with_icons = [f"{category_icons.get(cat, '📋')} {cat}" for cat in category_options]
    
    selected_cat_with_icon = st.sidebar.selectbox(
        "Select Category",
        options=category_options_with_icons,
        index=0,
        help="Choose a task category"
    )
    
    # Extract category name without icon
    selected_category = selected_cat_with_icon.split(" ", 1)[1]
    
    # Display tasks for the selected category
    st.sidebar.markdown("### Available Tasks")
    selected_task = st.sidebar.selectbox(
        "Select Task",
        options=departments[selected_department][selected_category],
        index=0,
        help="Choose a specific task to generate"
    )

    # Add the slider for number of tasks with better styling
    st.sidebar.markdown("### Task Configuration")
    n_tasks = st.sidebar.slider(
        "Number of Tasks to Generate",
        min_value=1,
        max_value=10,
        value=1,
        help="Select how many task instances to generate"
    )
    
    # Checkbox for terminal output with improved styling
    terminal = st.sidebar.checkbox(
        "Show Terminal Output",
        value=False,
        help="Display real-time terminal output during task generation"
    )
    
    # Divider
    st.sidebar.markdown("---")
    
    # Version info in sidebar footer
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 1rem 0; opacity: 0.7; font-size: 0.8rem;">
        Enterprise Task Generator v1.0.0<br>
        © 2025 Enterprise Systems
    </div>
    """, unsafe_allow_html=True)
    
    
    
    # Get the actual task key from the display name
    task_key = task_display_map.get(selected_task, selected_task)
    
    # Show the command that will be executed with nicer formatting
    if task_key in COMMANDS:
        st.markdown("### Command Preview")
        command_with_n = f"{COMMANDS[task_key]} --n {n_tasks}"
        st.code(command_with_n, language="bash")
    
    # Add a styled run button
    if st.button("🚀 Generate Task", help="Click to start task generation"):
        # Create a progress indicator
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Update progress
        status_text.text("Initializing task generation...")
        progress_bar.progress(10)
        
        # Run the command
        status_text.text("Executing task generator...")
        progress_bar.progress(30)
        
        success, message = run_command(task_key, n_tasks, terminal)
        progress_bar.progress(70)
        
        if success:
            # Success state
            progress_bar.progress(100)
            status_text.empty()
            
            st.markdown("""
            <div class="success-box">
                <strong>✅ Success!</strong> Task generation completed successfully.
            </div>
            """, unsafe_allow_html=True)
            
            if terminal:
                # Display terminal output in a collapsible section
                with st.expander("🖥️ View Complete Terminal Output", expanded=False):
                    st.markdown("""
                    <div class="terminal">
                    """ + message.replace('\n', '<br>') + """
                    </div>
                    """, unsafe_allow_html=True)
            
            # Try to display the output file
            output_path = extract_output_path(COMMANDS[task_key])
            progress_bar.progress(85)
            
            st.markdown("### Generated Task Output")
            output_data = display_output_file(output_path)
            progress_bar.progress(100)
            
            # Display JSON with better formatting
            if isinstance(output_data, dict) or isinstance(output_data, list):
                st.json(output_data)
            else:
                st.write(output_data)
        else:
            # Error state
            progress_bar.progress(100)
            status_text.empty()
            
            st.markdown("""
            <div class="error-box">
                <strong>❌ Error:</strong> Task generation failed.
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("🔍 View Error Details", expanded=True):
                st.code(message)
    
    # Display helpful tips at the bottom
    with st.expander("📌 Tips & Help", expanded=False):
        st.markdown("""
        ### Tips for Task Generation
        
        - **Task Selection**: Choose the appropriate department and category for your needs
        - **Number of Tasks**: Start with 1-2 tasks for testing, increase as needed
        - **Terminal Output**: Enable this option to see detailed progress and debugging information
        - **Task Output**: The generated JSON can be used as input for your enterprise applications
        
        Need more help? Contact the system administrator or visit the documentation portal.
        """)

if __name__ == "__main__":
    main()