# 🏢 EnterpriseBench: Evaluating LLM Agents in Simulated Enterprise Environments

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)

EnterpriseBench is a comprehensive framework designed to evaluate Large Language Model (LLM) agents within realistic enterprise environments. It provides a complete ecosystem for generating, simulating, and evaluating enterprise tasks across multiple business domains including HR, IT, Sales, Software Engineering, and Business Operations.

## 🌟 Key Features

- **🎯 Realistic Enterprise Simulation**: Comprehensive sandbox environment with authentic business data
- **🔄 Automated Task Generation**: Dynamic creation of enterprise tasks across multiple domains
- **📊 Multi-Domain Coverage**: HR, IT Service Management, CRM, Software Engineering, and Business Operations
- **🔍 Dual Evaluation Modes**: Search-based and CRUD-based task evaluation
- **🌐 Interactive Web Interface**: Streamlit-powered demos for easy interaction and visualization
- **📈 Scalable Architecture**: Supports evaluation of various LLM agents and frameworks

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Virtual environment (recommended)
- Required API keys (AWS, Azure AI)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://anonymous.4open.science/r/EnterpriseBench-87B1.git
   cd EnterpriseBench
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   cd Code
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create `.env` files in the respective demo directories with your API keys:
   ```bash
   AWS_KEY=your_aws_key_here
   AWS_SECRET_KEY=your_aws_secret_key_here
   AWS_REGION=your_aws_region_here
   api_base_azure_ai=your_azure_api_base_key_here
   api_key_azure=your_azure_api_key_here
   ```

### Running the Demos

#### 🎲 Task Generation Demo
Generate enterprise tasks dynamically across different departments:
```bash
cd "Code/TaskGeneration"
streamlit run task_gen_app.py
```

#### 📝 CRUD Evaluation Demo
Evaluate LLM agents on Create, Read, Update, Delete operations:
```bash
cd "Code/Simulation/CrudEvaluation"
streamlit run crud_demo.py
```

#### 🔍 Search Evaluation Demo
Test information retrieval and analysis capabilities:
```bash
cd "Code/Simulation/SearchEvaluation"
streamlit run search_demo.py
```

## 📁 Repository Structure

```
EnterpriseBench/
├── 📂 Code/                           # Implementation and demos
│   ├── 📂 TaskGeneration/             # Automated task generation system
│   │   ├── 📂 Access_Control/         # Department-specific access controls
│   │   ├── 📂 Business_and_Management/# Business domain task generators
│   │   ├── 📂 Human_Resource_Management/ # HR-specific task generation
│   │   ├── 📂 IT_Service_Management/  # IT service task generators
│   │   ├── 📂 Customer_Relation_Management/ # CRM task generators
│   │   ├── 📂 Enterprise_mail_system/ # Email system task generators
│   │   ├── 📂 Collaboration_tools/    # Collaboration task generators
│   │   ├── 📂 Workspace/              # Software engineering tasks
│   │   ├── 📄 task_gen_app.py         # Main Streamlit application
│   │   └── 📄 README.md               # Task generation documentation
│   ├── 📂 Simulation/                 # Evaluation frameworks
│   │   ├── 📂 CrudEvaluation/         # CRUD operation evaluation
│   │   ├── 📂 SearchEvaluation/       # Search task evaluation
│   │   └── 📄 README.md               # Simulation documentation
│   ├── 📄 requirements.txt            # Python dependencies
│   └── 📄 README.md                   # Code execution guide
├── 📂 Data/                           # Enterprise sandbox data and tasks
│   ├── 📂 EnterpriseSandbox/          # Realistic enterprise datasets
│   │   ├── 📂 Business_and_Management/# Business records and partnerships
│   │   ├── 📂 Human_Resource_Management/ # Employee records and HR data
│   │   ├── 📂 IT_Service_Management/  # IT helpdesk and incident data
│   │   ├── 📂 Customer_Relation_Management/ # Customer support and CRM
│   │   ├── 📂 Enterprise_mail_system/ # Internal email communications
│   │   ├── 📂 Collaboration_tools/    # Inter-departmental communications
│   │   ├── 📂 Enterprise Social Platform/ # Corporate social network data
│   │   ├── 📂 Policy_Documents/       # Company policies and guidelines
│   │   ├── 📂 Workspace/              # Software development repositories
│   │   └── 📂 Inazuma_Overflow/       # Internal Q&A platform
│   ├── 📂 EnterpriseTasks/            # Pre-generated evaluation tasks
│   │   ├── 📂 Business_Operations_Management/ # Business operation tasks
│   │   ├── 📂 HR_System/              # Human resources tasks
│   │   ├── 📂 IT_Solutions/           # IT service and support tasks
│   │   ├── 📂 SWE/                    # Software engineering tasks
│   │   └── 📂 Sales/                  # Sales and customer management tasks
│   └── 📄 README.md                   # Data documentation
└── 📄 README.md                       # This file
```

## 🎯 Use Cases

### For Researchers
- **LLM Agent Evaluation**: Benchmark different LLM agents on realistic enterprise tasks
- **Multi-Domain Analysis**: Compare performance across HR, IT, Sales, and Engineering domains
- **Task Complexity Studies**: Evaluate agents on varying complexity levels from simple searches to complex CRUD operations

### For Developers
- **Agent Development**: Test and refine LLM agents in controlled enterprise environments
- **Integration Testing**: Validate agent performance with real-world business data
- **Capability Assessment**: Identify strengths and limitations of different agent architectures

### For Enterprise Teams
- **AI Readiness Assessment**: Evaluate organizational readiness for LLM agent deployment
- **Use Case Identification**: Discover optimal applications for LLM agents in enterprise workflows
- **Risk Assessment**: Understand potential challenges and limitations before deployment

## 🔧 Technical Architecture

### Task Generation System
- **Dynamic Task Creation**: Automatically generates tasks based on department and complexity requirements
- **Configurable Parameters**: Customizable task types, difficulty levels, and domain focus
- **JSON Output Format**: Structured task definitions for easy integration with evaluation systems

### Evaluation Framework
- **Search Tasks**: Information retrieval, conversation analysis, and database queries
- **CRUD Tasks**: Create, Read, Update, Delete operations on enterprise data
- **Cross-Domain Integration**: Tasks that span multiple business domains
- **Performance Metrics**: Comprehensive evaluation criteria for agent assessment

### Data Infrastructure
- **Realistic Datasets**: Authentic enterprise data across 10+ business domains
- **Scalable Storage**: Organized data structure supporting various task types
- **Privacy-Compliant**: Synthetic data ensuring privacy while maintaining realism

## 📊 Supported Domains

| Domain | Description | Task Types | Data Sources |
|--------|-------------|------------|--------------|
| **Human Resources** | Employee management, recruitment, policies | Search, CRUD, Communication | Employee records, resumes, policies |
| **IT Service Management** | Helpdesk, incident management, system administration | Search, CRUD, Troubleshooting | Tickets, incident reports, system logs |
| **Customer Relations** | Customer support, sales, relationship management | Search, CRUD, Analysis | Support conversations, orders, reviews |
| **Software Engineering** | Code management, issue tracking, collaboration | Search, CRUD, Code Review | GitHub repositories, issues, discussions |
| **Business Operations** | Project management, partnerships, strategic planning | Search, CRUD, Analysis | Client records, partnerships, POCs |
| **Enterprise Communications** | Email systems, collaboration tools, social platforms | Search, CRUD, Communication | Email threads, chat logs, social posts |

## 🤝 Contributing

We welcome contributions to EnterpriseBench! Please see our contributing guidelines for more information on how to:

- Report bugs and request features
- Submit code improvements
- Add new enterprise domains
- Enhance evaluation metrics
- Improve documentation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/) for interactive web interfaces
- Powered by various LLM frameworks including OpenAI, Anthropic, and Azure AI
- Enterprise data simulation inspired by real-world business scenarios

## 📞 Support

For questions, issues, or collaboration opportunities:

- 📧 Create an issue in this repository
- 💬 Join our community discussions
- 📖 Check the detailed documentation in each component's README

---

**EnterpriseBench** - Bridging the gap between LLM capabilities and enterprise reality.
