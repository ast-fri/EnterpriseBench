---
layout: default
title: "Can LLMs Help You at Work? A Sandbox for Evaluating LLM Agents in Enterprise Environments"
---

<div class="nav-menu">
<header class="header">
      <div class="author-list-formal">
        <div class="author-names">
          Harsh Vishwakarma<span class="sup">1,&#42;</span>,
          Ankush Agarwal<span class="sup">1,&#42;</span>,
          Ojas F. Patil<span class="sup">1</span>,
          Chaitanya Devaguptapu<span class="sup">1</span>
          Mahesh Chandran<span class="sup">1</span>
        </div>
        <div class="affiliations">
          <span class="sup">1</span>Fujitsu Research India &nbsp;&nbsp;
        </div>
        <div class="author-footnote">
          <span class="sup">&#42;</span>Equal contribution &nbsp;&nbsp;
        </div>
      </div>
      <div class="links-section">
        <a href="https://github.com/ast-fri/EnterpriseBench" class="link-button github"><span>📄</span> GitHub</a>
        <a href="https://huggingface.co/datasets/AST-FRI/needles-in-images" class="link-button huggingface"><span>🤗</span> Hugging Face</a>
        <a href="https://aclanthology.org/2025.acl-long.1152/" class="link-button arxiv"><span>📚</span> Paper </a>
      </div>
    </header>
  <ul>
    <li><a href="#abstract">Abstract</a></li>
    <li><a href="#introduction">Introduction</a></li>
    <li><a href="#framework">EnterpriseBench Framework</a></li>
    <li><a href="#domains">Supported Domains</a></li>
    <li><a href="#evaluation">Evaluation Methods</a></li>
    <li><a href="#demos">Interactive Demos</a></li>
    <li><a href="#implementation">Implementation</a></li>
    <li><a href="#authors">Authors</a></li>
    <li><a href="#citation">Citation</a></li>
  </ul>
</div>

## Abstract {#abstract}

Enterprise systems are crucial for enhancing productivity and decision-making among employees and customers. Integrating LLM based systems into enterprise systems enables intelligent automation, personalized experiences, and efficient information retrieval, driving operational efficiency and strategic growth. However, developing and evaluating such systems is challenging due to the inherent complexity of enterprise environments, where data is fragmented across multiple sources and governed by sophisticated access controls.

Our benchmark features **EnerpriseBench** which provides a **Enteprise Simulation Environment** along with **500 Realistic Tasks** for comprehensive agent assessment. Through extensive evaluation across multiple domains, EnterpriseBench reveals significant gaps between current LLM agent capabilities and enterprise requirements, establishing new benchmarks for real-world AI deployment readiness.

<div class="highlight-box">
  <p><strong>🎯 Key Contributions:</strong></p>
  <ul>
    <li><strong>Realistic Enterprise Simulation:</strong> Comprehensive sandbox with authentic business data across 10+ domains</li>
    <li><strong>Diverse Tasks across Domains:</strong> Search-based and CRUD-based task assessment across different domains</li>
    <li><strong>Automated Task Generation:</strong> Dynamic creation of enterprise tasks with configurable complexity</li>
  </ul>
</div>

## Introduction {#introduction}

The deployment of LLM agents in enterprise environments presents unique challenges that current benchmarks fail to address. While existing evaluation frameworks focus on isolated capabilities like question-answering or code generation, real enterprise scenarios require agents to navigate complex, interconnected business systems with authentic data relationships and domain-specific constraints.

### Why Enterprise-Specific Evaluation Matters

Enterprise environments are characterized by:
- **Multi-domain Integration**: Tasks often span HR, IT, Sales, and Engineering departments
- **Complex Data Relationships**: Information is interconnected across multiple business systems
- **Domain-Specific Constraints**: Each department has unique workflows, terminology, and requirements
- **Realistic Scale**: Enterprise data volumes and complexity far exceed academic benchmarks

**EnterpriseBench** addresses these gaps by providing the first comprehensive framework specifically designed for enterprise LLM agent evaluation.


![EnterpriseBench Agent Workflow](assets/images/Enterprise Workflow.png)
*Figure 1: EnterpriseBench agent workflow showing the complete task execution process from user query through planning, execution, and task completion within the enterprise environment.*

## EnterpriseBench Framework {#framework}

### Architecture Overview

EnterpriseBench consists of three core components working together to provide comprehensive enterprise agent evaluation:

#### 1. **Enterprise Sandbox Environment**
- **Realistic Data**: Synthetic but authentic business data across 10+ domains
- **Interconnected Systems**: Data relationships mirror real enterprise architectures  
- **Scalable Infrastructure**: Supports various task types and complexity levels
- **Privacy-Compliant**: Synthetic data ensures privacy while maintaining realism

#### 2. **Dual Evaluation Framework**
- **Search Tasks**: Information retrieval, conversation analysis, and database queries
- **CRUD Tasks**: Create, Read, Update, Delete operations on enterprise data
- **Performance Metrics**: Comprehensive evaluation criteria for agent assessment
- **Interactive Interfaces**: Streamlit-powered demos for real-time evaluation

#### 3. **Dual Evaluation Framework**
- **Search Tasks**: Information retrieval, conversation analysis, and database queries
- **CRUD Tasks**: Create, Read, Update, Delete operations on enterprise data
- **Performance Metrics**: Comprehensive evaluation criteria for agent assessment
- **Interactive Interfaces**: Streamlit-powered demos for real-time evaluation


## Supported Domains {#domains}

EnterpriseBench covers comprehensive business domains with authentic data and realistic task scenarios:

| Domain | Description | Task Types | Data Sources |
|--------|-------------|------------|--------------|
| **🏢 Human Resources** | Employee management, recruitment, policies | Search, CRUD, Communication | Employee records, resumes, policies |
| **💻 IT Service Management** | Helpdesk, incident management, system administration | Search, CRUD, Troubleshooting | Tickets, incident reports, system logs |
| **🤝 Customer Relations** | Customer support, sales, relationship management | Search, CRUD, Analysis | Support conversations, orders, reviews |
| **⚙️ Software Engineering** | Code management, issue tracking, collaboration | Search, CRUD, Code Review | GitHub repositories, issues, discussions |
| **📊 Business Operations** | Project management, partnerships, strategic planning | Search, CRUD, Analysis | Client records, partnerships, POCs |
| **📧 Enterprise Communications** | Email systems, collaboration tools, social platforms | Search, CRUD, Communication | Email threads, chat logs, social posts |



## Evaluation Methods {#evaluation}

### Search-Based Evaluation

**Search tasks** evaluate an agent's ability to find, analyze, and synthesize information across enterprise systems:

- **Information Retrieval**: Locate specific data points across multiple systems
- **Conversation Analysis**: Extract insights from communication threads
- **Database Queries**: Navigate complex data relationships
- **Cross-Domain Search**: Find information spanning multiple departments

### CRUD-Based Evaluation  

**CRUD tasks** assess an agent's capability to perform standard business operations:

- **Create**: Generate new records, documents, or communications
- **Read**: Access and interpret existing business data
- **Update**: Modify records while maintaining data integrity
- **Delete**: Remove outdated or incorrect information safely

### Performance Results

**Table 3: EnterpriseBench Evaluation - Comparison of performance across agents using different models and planning strategies with LangChain and DSPy frameworks**

<div class="performance-table">
<table>
<thead>
<tr>
<th rowspan="2"><strong>Model</strong></th>
<th colspan="4"><strong>GPT-4 Evaluator</strong></th>
<th colspan="4"><strong>Gemini Evaluator</strong></th>
</tr>
<tr>
<th><strong>w/o Planning</strong></th>
<th><strong>CoT</strong></th>
<th><strong>ReAct</strong></th>
<th style="background-color: #f0f0f0;"><strong>w/ Gold Planning</strong></th>
<th><strong>w/o Planning</strong></th>
<th><strong>CoT</strong></th>
<th><strong>ReAct</strong></th>
<th style="background-color: #f0f0f0;"><strong>w/ Gold Planning</strong></th>
</tr>
</thead>
<tbody>
<tr style="background-color: #e6f3ff;">
<td colspan="9"><strong>LangChain Framework</strong></td>
</tr>
<tr style="background-color: #f0f8ff;">
<td><strong>GPT-4o</strong></td>
<td>0.29</td>
<td>0.27</td>
<td>0.32</td>
<td style="background-color: #f0f0f0;"><strong>0.43</strong></td>
<td>0.27</td>
<td>0.28</td>
<td>0.29</td>
<td style="background-color: #f0f0f0;">0.34</td>
</tr>
<tr style="background-color: #f0f8ff;">
<td><strong>Claude-3.5-Sonnet</strong></td>
<td>0.31</td>
<td>0.27</td>
<td>0.28</td>
<td style="background-color: #f0f0f0;">0.38</td>
<td>0.32</td>
<td>0.30</td>
<td>0.30</td>
<td style="background-color: #f0f0f0;"><strong>0.41</strong></td>
</tr>
<tr style="background-color: #f0f8ff;">
<td><strong>o1-mini</strong></td>
<td>0.31</td>
<td>0.28</td>
<td>0.35</td>
<td style="background-color: #f0f0f0;"><strong>0.51</strong></td>
<td>0.28</td>
<td>0.27</td>
<td>0.32</td>
<td style="background-color: #f0f0f0;">0.47</td>
</tr>
<tr style="background-color: #f0f8ff;">
<td><strong>Llama-3.1-8B</strong></td>
<td>0.04</td>
<td>0.06</td>
<td><strong>0.14</strong></td>
<td style="background-color: #f0f0f0;">0.20</td>
<td>0.03</td>
<td>0.04</td>
<td>0.09</td>
<td style="background-color: #f0f0f0;"><strong>0.21</strong></td>
</tr>
<tr style="background-color: #f0f8ff;">
<td><strong>Llama-3.3-70B</strong></td>
<td>0.23</td>
<td>0.22</td>
<td>0.21</td>
<td style="background-color: #f0f0f0;"><strong>0.40</strong></td>
<td>0.24</td>
<td>0.23</td>
<td>0.23</td>
<td style="background-color: #f0f0f0;">0.36</td>
</tr>
<tr style="background-color: #e6ffe6;">
<td colspan="9"><strong>DSPy</strong></td>
</tr>
<tr style="background-color: #f0fff0;">
<td><strong>GPT-4o</strong></td>
<td>0.19</td>
<td>0.32</td>
<td>0.34</td>
<td style="background-color: #f0f0f0;"><strong>0.50</strong></td>
<td>0.25</td>
<td>0.26</td>
<td>0.27</td>
<td style="background-color: #f0f0f0;">0.47</td>
</tr>
<tr style="background-color: #f0fff0;">
<td><strong>Claude-3.5-Sonnet</strong></td>
<td>0.19</td>
<td>0.24</td>
<td>0.30</td>
<td style="background-color: #f0f0f0;"><strong>0.50</strong></td>
<td>0.21</td>
<td>0.29</td>
<td>0.26</td>
<td style="background-color: #f0f0f0;">0.44</td>
</tr>
<tr style="background-color: #f0fff0;">
<td><strong>o1-mini</strong></td>
<td>0.29</td>
<td>0.33</td>
<td>0.38</td>
<td style="background-color: #f0f0f0;">0.62</td>
<td>0.27</td>
<td>0.32</td>
<td>0.41</td>
<td style="background-color: #f0f0f0;"><strong>0.63</strong></td>
</tr>
<tr style="background-color: #f0fff0;">
<td><strong>Llama-3.1-8B</strong></td>
<td>0.10</td>
<td>0.15</td>
<td>0.15</td>
<td style="background-color: #f0f0f0;">0.34</td>
<td>0.07</td>
<td>0.14</td>
<td>0.16</td>
<td style="background-color: #f0f0f0;"><strong>0.34</strong></td>
</tr>
<tr style="background-color: #f0fff0;">
<td><strong>Llama-3.3-70B</strong></td>
<td>0.20</td>
<td>0.27</td>
<td>0.30</td>
<td style="background-color: #f0f0f0;">0.47</td>
<td>0.24</td>
<td>0.25</td>
<td>0.28</td>
<td style="background-color: #f0f0f0;"><strong>0.48</strong></td>
</tr>
</tbody>
</table>
</div>


## Interactive Demos {#demos}

EnterpriseBench provides three interactive Streamlit applications for hands-on agent evaluation:

### 🎲 Task Generation Demo

Experience automated task creation across different enterprise domains:

<div class="card">
  <h4>Task Generation Features:</h4>
  <ul>
    <li><strong>Department Selection:</strong> Choose from 6 major business domains</li>
    <li><strong>Complexity Control:</strong> Adjust task difficulty and scope</li>
    <li><strong>Real-time Generation:</strong> Create tasks dynamically based on parameters</li>
    <li><strong>JSON Export:</strong> Download generated tasks for evaluation</li>
  </ul>
  
  <div class="video-container">
    <iframe width="560" height="315" src="https://www.youtube.com/embed/nKsPsowAugA" 
            title="EnterpriseBench Task Generation" frameborder="0" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
            allowfullscreen></iframe>
  </div>
  <p><strong>Demo Video:</strong> Watch how EnterpriseBench automatically generates Search-type tasks for the Engineering department using GitHub data sources.</p>
</div>

### 🔍 Search Evaluation Demo

Test agent capabilities on information retrieval and analysis tasks:

<div class="card">
  <h4>Search Evaluation Features:</h4>
  <ul>
    <li><strong>Multi-Domain Queries:</strong> Search across HR, IT, Sales, and Engineering data</li>
    <li><strong>Complex Relationships:</strong> Navigate interconnected business data</li>
    <li><strong>Real-time Results:</strong> See agent performance in real-time</li>
    <li><strong>Performance Analytics:</strong> Detailed metrics and failure analysis</li>
  </ul>
  
  <div class="video-container">
    <iframe width="560" height="315" src="https://www.youtube.com/embed/abiH1fzN3CE" 
            title="Simulating the Enterprise: LLM Agents at Work" frameborder="0" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
            allowfullscreen></iframe>
  </div>
  <p><strong>Demo Video:</strong> See an agent formulate plans, select tools, and complete search tasks within the enterprise simulation.</p>
</div>

### 📝 CRUD Evaluation Demo

Evaluate agent performance on standard business operations:

<div class="card">
  <h4>CRUD Evaluation Features:</h4>
  <ul>
    <li><strong>Business Operations:</strong> Create, read, update, and delete enterprise records</li>
    <li><strong>Data Integrity:</strong> Ensure operations maintain business rules</li>
    <li><strong>Multi-Step Tasks:</strong> Complex operations requiring multiple actions</li>
    <li><strong>Error Handling:</strong> Test agent responses to edge cases and errors</li>
  </ul>
  
  <div class="video-container">
    <iframe width="560" height="315" src="https://www.youtube.com/embed/TmHOhBErRCE" 
            title="Simulating the Enterprise: LLM Agents Sending a Mail" frameborder="0" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
            allowfullscreen></iframe>
  </div>
  <p><strong>Demo Video:</strong> Watch an IT employee use an agent to draft and send an email regarding a ticket issue, demonstrating CRUD operations in action.</p>
</div>


## Authors {#authors}

**EnterpriseBench** is developed by researchers focused on practical AI deployment in enterprise environments.

*Author information and affiliations will be revealed upon publication acceptance.*

## How to Cite {#citation}

If you use EnterpriseBench in your research, please cite our work:

```bibtex
@inproceedings{enterprisebench2025,
    title = "Can LLMs Help You at Work? A Sandbox for Evaluating LLM Agents in Enterprise Environments",
     author = "Vishwakarma, Harsh  and
      Agarwal, Ankush  and
      Ojas,F , Patil  and
      Devaguptapu, Chaitanya and
      Chandran, Mahesh"
    booktitle = "Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing",
    month = nov,
    year = "2025",
    address = "Suzhou, Suzhou",
    publisher = "Empirical Methods in Natural Language Processing",
   
}
```

---
<div class="highlight-box text-center">
  <h3>🚀 Ready to Evaluate Your LLM Agents?</h3>
  <p>EnterpriseBench provides the most comprehensive framework for testing LLM agents in realistic enterprise environments. Start evaluating today!</p>
</div>