# <img src="assets/images/agent.png" alt="EnterpriseBench" width="50"/> Can LLMs Help You at Work? A Sandbox for Evaluating LLM Agents in Enterprise Environments

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)

EnterpriseBench is a comprehensive framework designed to evaluate Large Language Model (LLM) agents within realistic enterprise environments. It provides a complete ecosystem for generating, simulating, and evaluating enterprise tasks across multiple business domains including HR, IT, Sales, Software Engineering, and Business Operations.

<p align="center">
  <img src="assets/images/EnterpriseWorkflow.gif" alt="EnterpriseBench Workflow" width="800"/>
</p>

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
   git clone https://github.com/ast-fri/EnterpriseBench.git
   cd EnterpriseBench
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create `.env` files in the respective demo directories with your API keys:
   ```env
   AWS_KEY=your_aws_key_here
   AWS_SECRET_KEY=your_aws_secret_key_here
   AWS_REGION=your_aws_region_here
   api_base_azure_ai=your_azure_api_base_key_here
   api_key_azure=your_azure_api_key_here
   ```

### Running the Demo

Generate enterprise tasks dynamically across different departments:
#### Using Command-line
```bash
python -m Task_Generation.runner
```
#### Using streamlit app
```bash
cd Task_Generation
streamlit run task_gen_app.py
```
### Evaluating the model
1. Create .env using .env.example
2. Select the mode of evaluation
3. run evaluation
```bash
"For batch evaluation"
python -m Evaluate.client 

"For interactive session"
python -m Evaluate.client -i

```

## 📁 Repository Structure

```
EnterpriseBench/
├── 📂 assets/                         # Static assets and resources
├── 📂 Business_and_Management/        # Business records and partnerships data
├── 📂 Collaboration_tools/            # Inter-departmental communications data
├── 📂 Customer_Relation_Management/   # Customer support and CRM data
├── 📂 Enterprise_mail_system/         # Internal email communications data
├── 📂 Enterprise Social Platform/     # Corporate social network data
├── 📂 Human_Resource_Management/      # Employee records and HR data
├── 📂 Inazuma_Overflow/               # Internal Q&A platform data
├── 📂 IT_Service_Management/          # IT helpdesk and incident data
├── 📂 Policy_Documents/               # Company policies and guidelines
├── 📂 Workspace/                      # Software development repositories
├── 📂 Task_Generation/                # Automated task generation system
│   ├── 📂 Config/                     # Configuration files
│   ├── 📂 Factories/                  # Task factory implementations
│   ├── 📂 generators/                 # Task generators for different domains
│   ├── 📂 Processors/                 # Task processing utilities
│   ├── 📂 utils/                      # Helper functions and utilities
│   ├── 📄 runner.py                   # Task generation runner
│   ├── 📄 task_gen_app.py             # Streamlit application
│   ├── 📄 tasks.json                  # Generated tasks (JSON format)
│   └── 📄 tasks.jsonl                 # Generated tasks (JSONL format)
├── 📂 _layouts/                       # Jekyll layout templates
├── 📄 _config.yml                     # Jekyll configuration
├── 📄 BLOG_README.md                  # Blog documentation
├── 📄 Gemfile                         # Ruby dependencies
├── 📄 index.md                        # Main index page
├── 📄 LICENSE                         # License file
├── 📄 README.md                       # This file
└── 📄 test.ipynb                      # Testing notebook
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

We welcome contributions to EnterpriseBench! Here's how you can help:

- **Report bugs**: Open an issue describing the bug and how to reproduce it
- **Request features**: Suggest new features or improvements via issues
- **Submit pull requests**: Contribute code improvements, new domains, or enhanced metrics
- **Improve documentation**: Help us make the docs clearer and more comprehensive

Please ensure your contributions align with our coding standards and include appropriate tests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/) for interactive web interfaces
- Powered by various LLM frameworks including OpenAI, Anthropic, and Azure AI
- Enterprise data simulation inspired by real-world business scenarios

## 📞 Support

For questions, issues, or collaboration opportunities:

- 📧 [Open an issue](https://github.com/ast-fri/EnterpriseBench/issues) in this repository
- 💬 Join our community discussions
- 📖 Check the detailed documentation in each component's README

## 🔗 Links

- **Repository**: [https://github.com/ast-fri/EnterpriseBench](https://github.com/ast-fri/EnterpriseBench)
- **Documentation**: See README files in individual component directories
- **Issues & Feedback**: [GitHub Issues](https://github.com/ast-fri/EnterpriseBench/issues)

## 📝 Citation

If you use EnterpriseBench in your research, please cite our paper:

```bibtex
@inproceedings{vishwakarma-etal-2025-llms,
    title = "Can {LLM}s Help You at Work? A Sandbox for Evaluating {LLM} Agents in Enterprise Environments",
    author = "Vishwakarma, Harsh  and
      Agarwal, Ankush  and
      Patil, Ojas  and
      Devaguptapu, Chaitanya  and
      Chandran, Mahesh",
    editor = "Christodoulopoulos, Christos  and
      Chakraborty, Tanmoy  and
      Rose, Carolyn  and
      Peng, Violet",
    booktitle = "Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing",
    month = nov,
    year = "2025",
    address = "Suzhou, China",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2025.emnlp-main.466/",
    pages = "9178--9212",
    ISBN = "979-8-89176-332-6",
}
```

---

**EnterpriseBench** - Bridging the gap between LLM capabilities and enterprise reality.