
# HIPAA Compliance Assistant

An AI powered HIPAA compliance assistant that uses LLMs, Retrieval Augmented Generation (RAG), and agentic reasoning to analyze healthcare privacy scenarios.

The application retrieves relevant HIPAA regulations from the official **Title 45 CFR XML dataset** and uses AI reasoning to determine whether a disclosure is permitted, denied, or uncertain.



## Features

### Multiple Reasoning Frameworks

The assistant supports three different approaches:

### Baseline
Uses the LLM's general HIPAA knowledge without external retrieval.

- Fast responses
- Tests model only reasoning
- Useful as a comparison baseline



### RAG (Retrieval Augmented Generation)

Uses TF-IDF retrieval over Title 45 CFR HIPAA regulations.

Pipeline:

1. User submits a HIPAA scenario
2. Relevant HIPAA sections are retrieved
3. Retrieved sections are provided to the LLM
4. Model generates a compliance decision based only on retrieved context

Benefits:

- Reduces hallucinated citations
- Grounds responses in regulatory text
- Provides relevant HIPAA sections



### Agentic Framework

Uses a multi step reasoning pipeline:

1. **Extractor Agent**
   - Identifies:
     - HIPAA topic
     - Entities involved
     - Action performed
     - Compliance issue

2. **Retrieval Step**
   - Finds relevant HIPAA sections

3. **Verdict Agent**
   - Makes the final compliance decision


## Installation

>[!IMPORTANT]
>The application requires a Hugging Face API token. Make sure to create an environment variable and save it to your computer.

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git

cd YOUR_REPOSITORY

python -m venv .venv

pip install -r requirements.txt

python -m streamlit run streamlit_test.py
```


