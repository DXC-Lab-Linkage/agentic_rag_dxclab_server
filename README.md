# Agentic RAG chatbot(Server)

- [Agentic RAG chatbot(Server)](#agentic-rag-chatbotserver)
  - [Overview](#overview)
  - [Screen Image](#screen-image)
  - [Features](#features)
  - [Graph Flow](#graph-flow)
  - [About the Source Code](#about-the-source-code)
  - [Environment Setup](#environment-setup)
    - [Products Used](#products-used)
    - [Setting Up the `venv` Virtual Environment](#setting-up-the-venv-virtual-environment)
    - [Preparing the `.env` File](#preparing-the-env-file)
  - [About the Vector DB for RAG](#about-the-vector-db-for-rag)
  - [Starting the Application](#starting-the-application)
  - [How to Modify Vector DB Data](#how-to-modify-vector-db-data)
    - [Registering Data to the Vector DB: create\_index.py](#registering-data-to-the-vector-db-create_indexpy)
      - [Modify the Description of Information Registered in the Vector DB](#modify-the-description-of-information-registered-in-the-vector-db)

## Overview

\* Japanese Guide: [README_ja.md](/README_ja.md)

- This is an Agentic RAG chatbot that effectively leverages internal company information and enables flexible thinking. Based on LangGraph, the AI Agent autonomously creates work plans and tasks, and provides optimal responses through RAG using web searches and a Vector DB. Unlike traditional one-question-one-answer systems, conversations and additional analyses can continue even after an answer is given. RAG is positioned as one of the tools the Agent invokes, much like web search.
- The Plan & Execution Agent pattern is also implemented, allowing the Agent to create its own search plan and execute appropriate search tools. This enables the collection of information from multiple angles in a systematic manner.

> Reference

- [What is agentic RAG?](https://www.ibm.com/think/topics/agentic-rag)
- [The 2025 Guide to AI Agents](https://www.ibm.com/think/ai-agents)

## Screen Image

On the left is the chatbot. On the right, the AI Agent’s thought process is displayed in real time.

![Screen image](/readme_images/screen_image.png)

## Features

- Since leaving operations entirely to the LLM can sometimes prevent convergence, we strictly manage the status of plans and set a maximum number of plans to ensure convergence.
- We extract and use only the necessary messages from AI messages and tool messages. By minimizing the messages the Agent references, costs can be reduced.
- By introducing the Plan & Execute pattern to create plans, information can be collected from multiple perspectives in a structured manner.
- AI agent can handle complex requests containing multiple items, resulting in structured responses.  
  Example: Collect technical information on Company A → Collect technical information on Company B → Compare technical information of Companies A and B.
- We use LangGraph. Since it can construct complex flows, it allows for customization to meet detailed requirements.
- A tool for searching arXiv papers is registered as one of the tool calling functions. Based on the user’s request, the Agent creates an arXiv search query and performs the search.

## Graph Flow

Below is the graph of the Agent created using LangGraph. Based on the user’s question or request, it determines whether to ask the user for clarification, whether the LLM itself should answer directly, or whether to conduct research using search.

1. AI Agent ask the user a question. (if there are unclear points in the request) [ask_human]
2. AI Agent answers directly as a LLM. [ans_llm_solo]
3. AI Agent searches.

   - Create one or more plans [create_plan]
   - Invoke tools based on the plan (tools: Tavily search web search, RAG, Arxiv paper search, LLM’s own response) [select_tool]
   - If no answer is obtained, recreate the plan [create_revised_plan]
   - Produce the final answer [create_final_answer]

![Graph](/readme_images/agent_graph.png)

## About the Source Code

The code is divided into two parts: frontend ([agentic_rag_client](https://github.com/DXC-Lab-Linkage/agentic_rag_dxclab_client) ) and backend ([agentic_rag_server](https://github.com/DXC-Lab-Linkage/agentic_rag_dxclab_server)). The code in this repository is the backend code.

## Environment Setup

Set up the backend environment as follows.

### Products Used

- Confirmed to work with Python versions 3.11 and 3.12.
- Uses Azure Open AI `gpt-4o` or `gpt-4o-mini`.
- Uses Tavily Search web search.
- Uses LangSmith. Not required.

### Setting Up the `venv` Virtual Environment

Create a virtual environment and dedicate the Python OSS installed to this application. This prevents affecting other applications and avoids errors due to OSS version dependencies.

> Windows

```Shell
cd <The root directory of the repository>
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
```

> Mac

```Shell
cd <The root directory of the repository>
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Preparing the `.env` File

Copy the `env.template` file and rename it to `.env`. Configure the settings according to your environment.

- Set `SESSION_SECRET_KEY` to a random string. Since it is used as a key, it is desirable to include both uppercase and lowercase letters and numbers, with approximately 16 characters. Use different values for each key.
- By setting `PROMPT_LANG`, `AGENT_THOUGHT_LANG`, `RAG_INDEX_LANG` and `FRONT_MSG_LANG`, you can switch the display between English and Japanese.
- Use `MAX_PLAN` to set the maximum number of Plans the Agent can create.
- If the Agent fails to find an answer on the first turn, it will re-plan for the next turn. The maximum number of turns can be configured with `MAX_TURN`.
- Documents retrieved via Web or RAG searches are truncated to the specified length (`MAX_SEARCH_TXT`) before being passed to the LLM, to reduce token consumption when the retrieved data is too large.
- Configure the Tavily Search–related parameters and the OpenAI parameters.
- For Tavily Search parameters, for example, setting `TAVILY_MAX_RESULTS=5` and `TAVILY_SEARCH_DEPTH=advanced` yields good search results. Setting it to `advanced` allows you to obtain more detailed information but doubles credit consumption. Therefore, when high-quality search results are not particularly necessary (e.g., during development), it is recommended to reduce the number of results and set it to `basic`. If you want to gather more information, increase the value of `TAVILY_MAX_RESULTS`.
- If you are using LangSmith, set `LANGSMITH_TRACING=true` and configure other LangSmith-related parameters. Use of LangSmith is not mandatory. Although LangSmith allows you to display detailed error information, the same information is also available in the application logs, so it is not a problem if you do not use it. Note that if you use LangSmith, data will be sent to LangSmith’s servers, so do not use it when handling internal or customer information. Use it only when dealing with dummy data.
- Set `AZURE_OPENAI_CHATGPT_DEPLOYMENT_NAME` to the model name. It supports `gpt-4o` or `gpt-4o-mini`.

```Text
# ----- Basic function -----
SESSION_SECRET_KEY=***
...
# Prompt language(EN: English, JA: Japanese)
PROMPT_LANG=EN
# Language of Agent thought process message(EN: English, JA: Japanese)
AGENT_THOUGHT_LANG=EN
# Language of front-end message(EN: English, JA: Japanese)
FRONT_MSG_LANG=EN
# Language of rag index data(EN: English, JA: Japanese)
RAG_INDEX_LANG=EN
# Parameters to control agent
MAX_PLAN=7
MAX_TURN=2
MAX_SEARCH_TXT=10000

...
# Tavily searchのAPI key(https://tavily.com/)
TAVILY_API_KEY=tvly-dev-***
TAVILY_MAX_RESULTS=5
# Tavily search search depth: basic or advanced
TAVILY_SEARCH_DEPTH=advanced

# --- OPENAI ---
AZURE_OPENAI_API_KEY=***
OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_ENDPOINT=***
AZURE_OPENAI_CHATGPT_DEPLOYMENT_NAME=gpt-4o

# --- LangSmith ---
# true: on, false: off
LANGSMITH_TRACING=false
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=***
LANGSMITH_PROJECT=pr-smug-tension-10
```

## About the Vector DB for RAG

The files `index.faiss` and `index.pkl` are located in `src\routers\agentic_rag\index`, and this data is used for searching. The search is performed by the `search_rag` function in `src\routers\agentic_rag\auto_research.py`.

## Starting the Application

- In the root folder of the backend, run:

```bash
uvicorn main:app
```

(Run pip install -r requirements.txt only when OSS dependencies change.)

- The server will start at `http://127.0.0.1:8000`.
- Start the frontend and navigate to `http://localhost:3000/`. For startup instructions, refer to the README.md of the frontend code `agentc_rag_dxclab_client`.

## How to Modify Vector DB Data

### Registering Data to the Vector DB: create_index.py

This script registers data to the Vector DB.

- This script reads txt, pdf, and md files within the `rag_docs` folder, creates an index, and saves it to `src\routers\agentic_rag\index`.
- Please store English documents in `rag_docs/en` and Japanese documents in `rag_docs/ja`.
- When you run `create_index.py`, you will be prompted with: `Choose language to index ('ja' or 'en'):` so please enter either `ja` or `en`. Two files, `index.faiss` and `index.pkl`, will then be created. If you enter `ja`, the files will be created in the `src\routers\agentic_rag\index\ja` folder; if you enter `en`, they will be created in the `src\routers\agentic_rag\index\en` folder.
- The index is created using the embedding model specified by the environment variable `HUG_EMBE_MODEL_NAME`.
- For text splitting, LangChain’s `CharacterTextSplitter` is used. It divides the document at the specified number of characters. If you need to change the splitting unit—such as splitting by document sections—customization is required.

#### Modify the Description of Information Registered in the Vector DB

In `auto_research.py`, the purpose of the Vector DB is described in the following three places. If you need to change the Vector DB data, update the purpose descriptions in these locations. The descriptions are placed in three spots to strictly control that the Agent only invokes the Vector DB when necessary. As initial data, information for three fictitious companies—GreenLife, Fic-NextFood, and Fic-TechFrontier—has been registered, so information relating to these companies is included.

> `vector_db_info` variable

Used when creating a plan in the `create_plan` prompt within `prompts_ja.yaml` and `prompts_en.yaml`. The purpose of the DB is described so that the Agent only performs a search of the Vector DB when necessary.

```Text
# To clearly communicate the information contained in the vector database and to prevent it from being used for other purposes
vector_db_info = "Internal company information for the fictional companies Fic-GreenLife, Fic-NextFood, and Fic-TechFrontier"
...
```

> `tool_info` variable

The Vector DB search is performed using the `search_rag` tool. The purpose of this tool is described.

```Text
# Write tool information. LLM read it and select tools to call.
tool_info = """
## Search Tools
The following tools are capable of searching only. Please do not call them for any other purpose.

- **ans_tavily**: Can perform web searches.
- **ans_arxiv**: Can search for papers published on arXiv.
- **search_rag**: Can only search the internal information of the three companies Fic-GreenLife, Fic-NextFood, and Fic-TechFrontier. It does not hold any information on other companies. If you need information on other companies, please use a different tool.

## Tools for LLM-Generated Responses
- **ans_llm_base**: Provides answers based on the LLM's own knowledge. It is capable of answering questions, summarizing, taking action on research findings, analyzing, extracting keywords, computing, offering opinions and insights, reasoning, and listing results.
...
```

> Docstring of the `def search_rag` function

Describes the purpose of this tool. Must be written in English.

```Text
    def search_rag(
        state: Annotated[State, InjectedState], config: RunnableConfig
    ) -> str:
        """
        Answer only internal information of 3 fictitious companies named Fic-GreenLife, Fic-NextFood and Fic-TechFrontier. When you want other companies information, use other tools because It can not answer other companies.

        Tool Specifications:
          - Purpose: When the user asks questions only for 3 companies like "What isFic-GreenLife?".

        Args:
          state: Annotated[State, InjectedState]
          config: RunnableConfig

        Returns:
          str: answer
        """
```
