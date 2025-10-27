---
layout: default
title: "EnterpriseBench: Evaluating LLM Agents in Enterprise Environments"
---

<div class="page-container">

# Can LLMs Help You at Work? 
## A Sandbox for Evaluating LLM Agents in Enterprise Environments

<div class="author-section">
  <div class="authors">
    Harsh Vishwakarma<sup>1,*</sup> &nbsp;&nbsp;
    Ankush Agarwal<sup>1,*</sup> &nbsp;&nbsp;
    Ojas Patil<sup>1</sup> &nbsp;&nbsp;
    Chaitanya Devaguptapu<sup>1</sup> &nbsp;&nbsp;
    Mahesh Chandran<sup>1</sup>
  </div>
  <div class="affiliations">
    <sup>1</sup>Fujitsu Research India
  </div>
  <div class="equal-contrib">
    <sup>*</sup>Equal contribution
  </div>
</div>

<div class="button-group">
  <a href="https://github.com/ast-fri/EnterpriseBench" class="btn btn-github">
    <span>📄</span> GitHub
  </a>
  <a href="https://huggingface.co/datasets/AST-FRI/EnterpriseBench" class="btn btn-huggingface">
    <span>🤗</span> Hugging Face
  </a>
</div>

---

## Overview

**EnterpriseBench** is a video-driven evaluation framework for LLM-based agents operating in realistic enterprise environments. It transforms complex business workflows into structured agent tasks—no manual annotation required. The framework detects business operations across multiple domains, reconstructs task parameters, and evaluates agents with comprehensive metrics across real enterprise scenarios.

---

## Key Features & Contributions

<div class="feature-grid">
  <div class="feature-card">
    <h3>🏢 Realistic Enterprise Simulation</h3>
    <p>Comprehensive sandbox with authentic business data across 10+ domains including HR, IT, Sales, Engineering, and more.</p>
  </div>
  
  <div class="feature-card">
    <h3>📊 Diverse Task Assessment</h3>
    <p>Search-based and CRUD-based task evaluation spanning different enterprise departments with complex data relationships.</p>
  </div>
  
  <div class="feature-card">
    <h3>🤖 Automated Task Generation</h3>
    <p>Dynamic creation of enterprise tasks with configurable complexity, enabling scalable agent evaluation.</p>
  </div>
</div>

---

## Enterprise Agent Workflow

See how EnterpriseBench agents navigate complex enterprise environments—from query understanding to multi-step task execution 🚀

<div class="video-wrapper">
  <img src="assets/images/EnterpriseWorkflow.gif" alt="EnterpriseBench Agent Workflow" />
  <p class="caption">EnterpriseBench agent workflow showing the complete task execution process from user query through planning, execution, and task completion.</p>
</div>

---

## The EnterpriseBench Pipeline

We build a scalable, domain-centric evaluation pipeline that covers the complete spectrum of enterprise operations.

### 📝 Enterprise Data Collection

Guided by **domain coherence**—the tendency of enterprise systems to maintain stable data relationships—we create realistic synthetic business data that mirrors real-world enterprise architectures.

Our pipeline generates **500 realistic tasks** across multiple business domains with authentic data relationships, covering ~10+ enterprise departments with interconnected systems.

### 🔍 Task Generation & Filtering

To ensure training-ready material, we apply **intelligent task filtering** that maintains task quality and relevance.

Specifically, we generate tasks where business operations are authentic, contextually grounded, and reflect real enterprise workflows. This process yields **high-quality evaluation tasks** spanning Search and CRUD operations.

### 🎯 Dual Evaluation Framework

**EnterpriseBench** provides comprehensive agent assessment through two complementary evaluation modes:

**(i)** Search-based evaluation with multi-domain queries and complex data relationships  
**(ii)** CRUD-based operations (Create, Read, Update, Delete) across enterprise systems  
**(iii)** Performance analytics with detailed metrics and failure analysis

---

## Two-Stage Agent Evaluation

We evaluate end-to-end computer-use agents with a **comprehensive framework** across our enterprise task set.

**Search Evaluation** assesses information retrieval on **diverse enterprise queries** from EnterpriseBench (500 tasks → spanning 10+ domains), testing multi-domain navigation and complex relationship understanding.

**CRUD Evaluation** validates business operations with curated task scenarios, while focused **data integrity checks** ensure agents maintain enterprise constraints and business rules.

This decoupled search→operations evaluation reveals both retrieval and action-execution capabilities: even state-of-the-art models like o1-mini with gold planning achieve only **62-63% success** on enterprise tasks, highlighting significant gaps between current AI and real-world enterprise requirements.

---

## Performance Results

<div class="results-section">

| Model | w/o Planning | CoT | ReAct | w/ Gold Planning |
|-------|--------------|-----|-------|------------------|
| **LangChain Framework** ||||  |
| GPT-4o | 0.29 | 0.27 | 0.32 | **0.43** |
| Claude-3.5-Sonnet | 0.31 | 0.27 | 0.28 | **0.38** |
| o1-mini | 0.31 | 0.28 | 0.35 | **0.51** |
| Llama-3.1-8B | 0.04 | 0.06 | 0.14 | **0.20** |
| Llama-3.3-70B | 0.23 | 0.22 | 0.21 | **0.40** |
| **DSPy Framework** ||||  |
| GPT-4o | 0.19 | 0.32 | 0.34 | **0.50** |
| Claude-3.5-Sonnet | 0.19 | 0.24 | 0.30 | **0.50** |
| o1-mini | 0.29 | 0.33 | 0.38 | **0.62** |
| Llama-3.1-8B | 0.10 | 0.15 | 0.15 | **0.34** |
| Llama-3.3-70B | 0.20 | 0.27 | 0.30 | **0.47** |

*Table: Performance comparison using GPT-4 evaluator across different models and planning strategies*

</div>

---

## Interactive Demonstrations

### 🎲 Task Generation Demo

<div class="demo-section">
  <div class="video-container">
    <iframe width="100%" height="400" src="https://www.youtube.com/embed/nKsPsowAugA" 
            title="EnterpriseBench Task Generation" frameborder="0" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
            allowfullscreen></iframe>
  </div>
  <p class="caption">Watch how EnterpriseBench automatically generates Search-type tasks for the Engineering department using GitHub data sources.</p>
</div>

### 🔍 Search Evaluation Demo

<div class="demo-section">
  <div class="video-container">
    <iframe width="100%" height="400" src="https://www.youtube.com/embed/abiH1fzN3CE" 
            title="Enterprise Agent Search Demo" frameborder="0" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
            allowfullscreen></iframe>
  </div>
  <p class="caption">See an agent formulate plans, select tools, and complete search tasks within the enterprise simulation.</p>
</div>

### 📝 CRUD Evaluation Demo

<div class="demo-section">
  <div class="video-container">
    <iframe width="100%" height="400" src="https://www.youtube.com/embed/TmHOhBErRCE" 
            title="Enterprise Agent CRUD Demo" frameborder="0" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
            allowfullscreen></iframe>
  </div>
  <p class="caption">Watch an IT employee use an agent to draft and send an email regarding a ticket issue, demonstrating CRUD operations.</p>
</div>

---

## Acknowledgments

We thank our colleagues at Fujitsu Research India for their valuable feedback and support throughout this project.

---

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
    address = "Suzhou, China",
    publisher = "Empirical Methods in Natural Language Processing",
   
}
```

---
<div class="highlight-box text-center">
  <h3>🚀 Ready to Evaluate Your LLM Agents?</h3>
  <p>EnterpriseBench provides the most comprehensive framework for testing LLM agents in realistic enterprise environments. Start evaluating today!</p>
</div>