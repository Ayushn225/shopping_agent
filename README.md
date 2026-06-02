# 🛍️ AI Shopping Assistant & Agent

An intelligent, agentic conversational shopping assistant built with **Streamlit**, **LangGraph / LangChain Agents**, and **Groq Cloud LLMs**. The assistant supports multimodal style discovery via image uploads, product evaluation by communicating with a local SQLite database, customer review aggregation, automated conversational preferences tracking, and a checkout workflow.

---

## 🛠️ Key Technical Enhancements

* **Smart Contextual Guardrails:** Migrated from a rigid, latency-heavy frontend guardrail function to a unified, context-aware instruction layer within the agent's core system prompt. It allows friendly small talk ("Hello, how are you?") while strictly blocking malicious or off-topic prompts (like creative writing or code execution requests).
* **High-Throughput Inference Architecture:** Upgraded the primary reasoning engine to `llama-3.3-70b-versatile` on Groq to handle complex tool coordination pipelines cleanly while avoiding Tokens Per Minute (TPM) constraint walls.
* **Dual-Layer Evals Suite:** Integrated localized automated precision testing consisting of:
  1. **Tool Call Accuracy Checks:** Multi-turn conversational mocks to assert accurate programmatic schema parsing and structural parameters routing.
  2. **Response Quality (LLM-as-a-Judge):** Validates markdown formatting structures and boundary condition compliance utilizing structured JSON evaluations.

---

## 🚀 Getting Started

This project is optimized to run with **`uv`**, a blazing-fast Python package installer and resolver.

### 📋 Prerequisites

Ensure you have Python 3.10+ and `uv` installed on your system. 
If you don't have `uv` installed, run:
* **macOS/Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
* **Windows:** `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

### 🛠️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Ayushn225/shopping_agent.git](https://github.com/Ayushn225/shopping_agent.git)
   cd shopping_agent
   ```

2. **Synchronize environment and packages:**
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -r requirements.txt
   
4. **Configure Environment Variables:**
   GROQ_API_KEY="your-groq-api-key-here"
   LANGSMITH_API_KEY="your-optional-langsmith-key" # If tracking via LangSmith


### 🖥️ Running the Application
To spin up the reactive Streamlit chat client interface, execute:
   ```bash
   uv run streamlit run app.py
   ```

### 🧪 Running the Evaluation Matrix
The evaluation infrastructure checks both parameter payload accuracy and text-generation formatting rules.

To run the full suite using your configured uv environment, run:
   ```bash
   uv run pytest test_agent_eval.py -v
   ```
