---
layout: default
title: "Can LLMs Help You at Work? A Sandbox for Evaluating LLM Agents in Enterprise Environments"
---

<style>
.page-container { max-width: 900px; margin: 0 auto; padding: 60px 20px; }
.main-title { font-size: 2.5em; font-weight: 700; text-align: center; margin-bottom: 0.2em; color: #1a1a1a; line-height: 1.2; }
.subtitle { font-size: 1.3em; font-weight: 400; text-align: center; margin-bottom: 1.5em; color: #555; line-height: 1.4; }
.author-section { text-align: center; margin: 2em 0 3em 0; }
.authors { font-size: 1.1em; margin-bottom: 0.8em; }
.affiliations { font-size: 0.95em; color: #666; margin-bottom: 0.5em; }
.equal-contrib { font-size: 0.9em; color: #888; font-style: italic; }
.button-group { display: flex; justify-content: center; gap: 15px; margin: 2em 0; flex-wrap: wrap; }
.btn { display: inline-flex; align-items: center; gap: 8px; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 0.95em; transition: all 0.3s ease; }
.btn-github { background: #24292e; color: white; }
.btn-github:hover { background: #1a1f23; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(36, 41, 46, 0.3); text-decoration: none; }
.btn-huggingface { background: #ff9d00; color: white; }
.btn-huggingface:hover { background: #e68a00; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(255, 157, 0, 0.3); text-decoration: none; }
.feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 25px; margin: 3em 0; }
.feature-card { padding: 25px; background: #f8f9fa; border-radius: 12px; border: 1px solid #e9ecef; transition: all 0.3s ease; }
.feature-card:hover { transform: translateY(-5px); box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1); }
.feature-card h3 { margin-top: 0; font-size: 1.2em; margin-bottom: 0.8em; }
.video-container { position: relative; width: 100%; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 12px; margin: 2em 0 1em 0; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1); }
.video-container iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0; }
.caption { font-size: 0.9em; color: #666; font-style: italic; text-align: center; margin-top: 1em; }
img { max-width: 100%; height: auto; border-radius: 12px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1); display: block; margin: 2em auto; }
table { width: 100%; border-collapse: collapse; margin: 1.5em 0; font-size: 0.9em; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05); border-radius: 8px; overflow: hidden; }
th, td { padding: 12px 15px; border-bottom: 1px solid #e9ecef; }
thead th { background-color: #f8f9fa; font-weight: 600; text-align: center; border-bottom: 2px solid #dee2e6; }
tbody tr:hover { background-color: #f8f9fa; }
td:first-child { font-weight: 600; text-align: left; }
td:not(:first-child) { text-align: center; font-family: "Courier New", monospace; }
@media (max-width: 768px) {
  .main-title { font-size: 1.8em; }
  .subtitle { font-size: 1.1em; }
  .feature-grid { grid-template-columns: 1fr; }
  .button-group { flex-direction: column; align-items: center; }
  .btn { width: 100%; max-width: 300px; justify-content: center; }
}
</style>

<div class="page-container">

<h1 class="main-title">Can LLMs Help You at Work?</h1>
<p class="subtitle">A Sandbox for Evaluating LLM Agents in Enterprise Environments</p>

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

**EnterpriseBench** provides a comprehensive evaluation framework for LLM-based agents operating in realistic enterprise environments. It features an enterprise simulation environment along with 500 realistic tasks for comprehensive agent assessment across multiple business domains.

Enterprise environments present unique challenges that current benchmarks fail to address, including multi-domain integration, complex data relationships, domain-specific constraints, and realistic scale that far exceeds academic benchmarks.

---

## Key Features

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

![EnterpriseBench Agent Workflow](assets/images/EnterpriseWorkflow.gif)

<p class="caption">EnterpriseBench agent workflow showing the complete task execution process from user query through planning, execution, and task completion.</p>

---

## The EnterpriseBench Pipeline

We build a scalable, domain-centric evaluation pipeline that covers the complete spectrum of enterprise operations.

### Enterprise Data Collection

Guided by **domain coherence**, we create realistic synthetic business data that mirrors real-world enterprise architectures. Our pipeline generates **500 realistic tasks** across multiple business domains with authentic data relationships, covering 10+ enterprise departments with interconnected systems.

### Dual Evaluation Framework

**EnterpriseBench** provides comprehensive agent assessment through two complementary evaluation modes:

- **Search-based evaluation** with multi-domain queries and complex data relationships
- **CRUD-based operations** (Create, Read, Update, Delete) across enterprise systems  
- **Performance analytics** with detailed metrics and failure analysis

This evaluation framework addresses enterprise-specific challenges including role-based access control, reliability guarantees, compliance requirements, and long-term interaction patterns that generic LLM benchmarks overlook.

---

## Performance Results

| Model | w/o Planning | CoT | ReAct | w/ Gold Planning |
|-------|--------------|-----|-------|------------------|
| **LangChain Framework** ||||
| GPT-4o | 0.29 | 0.27 | 0.32 | **0.43** |
| Claude-3.5-Sonnet | 0.31 | 0.27 | 0.28 | **0.38** |
| o1-mini | 0.31 | 0.28 | 0.35 | **0.51** |
| Llama-3.1-8B | 0.04 | 0.06 | 0.14 | **0.20** |
| Llama-3.3-70B | 0.23 | 0.22 | 0.21 | **0.40** |
| **DSPy Framework** ||||
| GPT-4o | 0.19 | 0.32 | 0.34 | **0.50** |
| Claude-3.5-Sonnet | 0.19 | 0.24 | 0.30 | **0.50** |
| o1-mini | 0.29 | 0.33 | 0.38 | **0.62** |
| Llama-3.1-8B | 0.10 | 0.15 | 0.15 | **0.34** |
| Llama-3.3-70B | 0.20 | 0.27 | 0.30 | **0.47** |

*Table: Performance comparison using GPT-4 evaluator across different models and planning strategies. Even state-of-the-art models like o1-mini with gold planning achieve only 62-63% success, highlighting significant gaps between current AI capabilities and enterprise requirements.*

---

## Interactive Demonstrations

### Task Generation Demo

<div class="video-container">
  <iframe src="https://www.youtube.com/embed/nKsPsowAugA" title="EnterpriseBench Task Generation" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
</div>

<p class="caption">Watch how EnterpriseBench automatically generates Search-type tasks for the Engineering department using GitHub data sources.</p>

### Search Evaluation Demo

<div class="video-container">
  <iframe src="https://www.youtube.com/embed/abiH1fzN3CE" title="Enterprise Agent Search Demo" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
</div>

<p class="caption">See an agent formulate plans, select tools, and complete search tasks within the enterprise simulation.</p>

### CRUD Evaluation Demo

<div class="video-container">
  <iframe src="https://www.youtube.com/embed/TmHOhBErRCE" title="Enterprise Agent CRUD Demo" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
</div>

<p class="caption">Watch an IT employee use an agent to draft and send an email regarding a ticket issue, demonstrating CRUD operations.</p>


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