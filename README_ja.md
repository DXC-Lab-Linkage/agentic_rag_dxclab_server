# Agentic RAG chatbot(Server)

- [Agentic RAG chatbot(Server)](#agentic-rag-chatbotserver)
  - [概要](#概要)
  - [画面イメージ](#画面イメージ)
  - [特徴](#特徴)
  - [Graph Flow](#graph-flow)
  - [ソースコードについて](#ソースコードについて)
  - [環境セットアップ](#環境セットアップ)
    - [使用プロダクト](#使用プロダクト)
    - [仮想環境 venv の設定](#仮想環境-venv-の設定)
    - [.env ファイルの準備](#env-ファイルの準備)
  - [RAG 用 Vector DB について](#rag-用-vector-db-について)
  - [アプリケーションの起動](#アプリケーションの起動)
  - [Vector DB データの変更方法](#vector-db-データの変更方法)
    - [Vector DB へのデータの登録：create_index.py](#vector-db-へのデータの登録create_indexpy)
      - [Vector DB に登録した情報の説明を変更](#vector-db-に登録した情報の説明を変更)
  - [バッチモードのドキュメント](#バッチモードのドキュメント)

## 概要

※ English guide: [README.md](/README.md)

- 社内情報を効果的に活用し、柔軟な思考が可能な Agentic RAG チャットボットです。LangGraph を基盤とした AI Agent が自律的に作業計画やタスクを立案し、Web 検索や Vector DB を用いた RAG により最適な回答を提供します。従来の一問一答にとどまらず、回答後も会話や追加分析が継続できる点が特徴です。RAG は Web 検索のように、Agent が呼び出すツールのひとつとして位置付けられます。
- Plan & Execution の Agent パターンも導入しており、Agent が自ら検索計画を作成して適切な検索ツールを実行します。それにより、多角的かつ体系的に情報を収集して回答することができます。

> 参考資料

- [What is agentic RAG?](https://www.ibm.com/think/topics/agentic-rag)
- [The 2025 Guide to AI Agents](https://www.ibm.com/think/ai-agents)

## 画面イメージ

左側がチャットボットです。右側には AI Agent の思考プロセスがリアルタイムに表示されます。

![Screen image](/readme_images/screen_image.png)

※ 日本語モードに切り替えると日本語で使用できます。

## 特徴

- 動作を LLM 任せにすると収束しないことがあるため、計画のステータスを厳格に管理します。確実に収束するよう、計画数の最大値も設定します。
- AI Message や Tool Message の中から必要なメッセージだけを抽出して利用します。Agent が参照するメッセージを最小限に抑えることで、コストを削減できます。
- Plan & Execute パターンを導入して計画を作成することで、多面的かつ体系的に情報を収集できます。
- 複数の内容を含む複雑な依頼にも対応可能で、回答が構造的になります。
  例：A 社の技術情報収集 → B 社の技術情報収集 → A・B 社の技術情報の比較
- LangGraph を使用しています。複雑なフローを構築できるため、細かい要件に合わせたカスタマイズが可能です。
- arxiv にある論文を検索するツールを Tool calling function の一つとして登録しています。ユーザーの依頼を基に Agent が arxiv 用の検索クエリーを作成して検索を行います。

## Graph Flow

以下は LangGraph を使用して作成された Agent の Graph です。ユーザーからの質問・依頼を基に、「ユーザーに不明点を確認するのか」、「LLM 自身が直接回答するのか」、「検索を使用して調査を行うのか」を判断します。

1. ユーザーに質問 (依頼内容に不明点がある場合) [ask_human]
2. LLM 自身が回答 [ans_llm_solo]
3. 検索
   - 計画作成 (複数可) [create_plan]
   - 計画を基にツールを呼び出す（ツール：Tavily search Web 検索、RAG、Arxiv 論文検索、LLM 自身の回答）[select_tool]
   - 回答が得られなければ計画を再作成 [create_revised_plan]
   - 最終回答の作成 [create_final_answer]

![Graph](/readme_images/agent_graph.png)

## ソースコードについて

コードがフロントエンド：[agentic_rag_client](https://github.com/DXC-Lab-Linkage/agentic_rag_dxclab_client) とバックエンド：[agentic_rag_server](https://github.com/DXC-Lab-Linkage/agentic_rag_dxclab_server) の 2 つに分かれています。当リポジトリーのコードはバックエンドのコードです。

## 環境セットアップ

バックエンドの環境を以下のようにセットアップします。

### 使用プロダクト

- Python version 3.11、3.12 で動作確認済みです。
- Azure Open AI の `gpt-4o`, `gpt-4o-mini` または `gpt-5-chat` を使用します。
- Tavily search の Web 検索を使用します。
- LangSmith を使用します。必須ではありません。

### 仮想環境 venv の設定

仮想環境を構築し、インストールする Python の OSS をこのアプリケーション専用にします。これにより、他のアプリケーションへの影響を防ぎ、OSS のバージョン依存関係によるエラーを回避できます。

> Windows

```Shell
cd <リポジトリのrootディレクトリ>
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
```

> Mac

```Shell
cd <リポジトリのrootディレクトリ>
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### .env ファイルの準備

`env.template` ファイルをコピーして、`.env` という名前に変更します。環境に合わせて設定を行います。

- `SESSION_SECRET_KEY` にはランダムな文字列を設定してください。鍵として使用するため、大小の英字と数字を含めた約 16 桁の文字列が望ましいです。それぞれ異なる値を設定してください。
- `PROMPT_LANG`、`AGENT_THOUGHT_LANG`、`FRONT_MSG_LANG`、`RAG_INDEX_LANG` を設定することで、英語または日本語の表示を切り替えることが可能です。**日本語で使用する場合は、`JA` の値をセットしてください。**
- `MAX_PLAN` によって、Agent が作成する Plan 数の最大値を設定できます。
- Agent が最初のターンで回答を見つけられなかった場合、次のターンとして再度 Plan を立て直します。その最大ターン数は `MAX_TURN` で設定できます。
- Web や RAG で検索した文書は、指定した長さ (`MAX_SEARCH_TXT`) で切り取られ、その後 LLM に渡される仕組みになっています。検索したデータが大きすぎると、トークンの消費量が多くなってしまうためです。
- Tavily Search 関連のパラメーターと OpenAI のパラメーターを設定してください。
- Tavily Search のパラメーターは、例えば `TAVILY_MAX_RESULTS=5`、`TAVILY_SEARCH_DEPTH=advanced` のように設定すると良い検索結果が得られます。`advanced` に設定すると、より詳細な情報を取得できますが、クレジットの消費量が 2 倍になります。そのため、開発中などで良い検索結果が特に必要ない場合は件数を減らし、`basic` を設定することをおすすめします。より多くの情報を集めたい場合は、`TAVILY_MAX_RESULTS` の値を大きくしてください。
- LangSmith を使用する場合は `LANGSMITH_TRACING=true` に設定し、他の LangSmith 関連のパラメーターも設定してください。LangSmith の使用は必須ではありません。LangSmith を使うとエラーの詳細を表示できますが、同様の情報はアプリのログにも表示されるため、使用しなくても特に問題ありません。なお、LangSmith を使用すると、LangSmith のサーバーにデータが送信されるため、社内情報やお客様の情報を扱う場合は使用しないでください。ダミーデータのみを扱う場合に限り、使用してください。
- `AZURE_OPENAI_CHATGPT_DEPLOYMENT_NAME` にモデル名を指定してください。`gpt-4o` または `gpt-4o-mini` で稼働します。

```Text
# ----- Basic function -----
SESSION_SECRET_KEY=***
...
# Prompt language(EN: English, JA: Japanese)
PROMPT_LANG=JA
# Language of Agent thought process message(EN: English, JA: Japanese)
AGENT_THOUGHT_LANG=JA
# Language of front-end message(EN: English, JA: Japanese)
FRONT_MSG_LANG=JA
# Language of rag index data(EN: English, JA: Japanese)
RAG_INDEX_LANG=JA
# Parameters to control agent
MAX_PLAN=5
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

## RAG 用 Vector DB について

`src\routers\agentic_rag\index` 内に `index.faiss` と `index.pkl` ファイルがあり、このデータを検索します。検索は `src\routers\agentic_rag\auto_research.py` 内の `search_rag` 関数で行います。

## アプリケーションの起動

- バックエンドのルートフォルダーで `uvicorn main:app` を実行します（`pip install -r requirements.txt` は OSS 変更時のみ）。サーバーは [http://127.0.0.1:8000](http://127.0.0.1:8000) で起動します。
- フロントエンドを起動し、URL [http://localhost:3000/](http://localhost:3000/) にアクセスします。起動方法はフロントエンド側コード `agentc_rag_dxclab_client` の README.md を参照してください。

## Vector DB データの変更方法

### Vector DB へのデータの登録：create_index.py

Vector DB へデータを登録します。

- この script が`rag_docs` フォルダー内の txt、pdf、md ファイルを読み込んでインデックスを作成し、`src\routers\agentic_rag\index` に保存します。
- 英語の文書は `rag_docs/en`、日本語の文書は `rag_docs/ja` に保管してください。
- `create_index.py` を実行すると、`Choose language to index ('ja' or 'en'):` のように聞かれるため、`ja` または `en` を入力してください。すると、`index.faiss` と `index.pkl` の 2 つのファイルが作成されます。`ja` を入力した場合は、`src\routers\agentic_rag\index\ja` フォルダーにファイルが作成され、`en` の場合は同じく `en` フォルダーに作成されます。
- インデックスは、環境変数 `HUG_EMBE_MODEL_NAME` で指定した埋め込みモデルを使用して作成します。
- テキストの分割には、LangChain の `CharacterTextSplitter` を使用します。指定した文字数ごとに文書を分割します。文書のセクションごとに分割するなど、分割単位を変更する場合はカスタマイズが必要です。

#### Vector DB に登録した情報の説明を変更

`auto_research.py` の以下の 3 箇所に Vector DB の用途を記載しています。Vector DB のデータを変更する場合は、これらの箇所の用途の説明を変更してください。
Agent が必要な時にだけ Vector DB を呼び出すように厳格に制御するために 3 箇所に記載しています。初期データとして、GreenLife, Fic-NextFood, and Fic-TechFrontier という架空の会社のデータを登録しているため、これらに関する情報が書かれています。

> `vector_db_info` 変数

`prompts_ja.yaml`, `prompts_en.yaml` 中の `create_plan` のプロンプトでプランを作成する際に使用されます。Agent が必要な時にだけ Vector DB の検索を行うために DB の用途を記載しています。

```Text
# To clearly communicate the information contained in the vector database and to prevent it from being used for other purposes
vector_db_info = "Internal company information for the fictional companies Fic-GreenLife, Fic-NextFood, and Fic-TechFrontier"
...
```

> `tool_info` 変数

Vector DB 検索は `search_rag` ツールを使用して行います。このツールの用途を記載しています。

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

> `def search_rag` 関数の Docstring

このツールの用途を記載しています。英語で記載する必要が有ります。

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

## バッチモードのドキュメント

バッチモード機能の使用方法については、[バッチモードのドキュメント](/README_batch_ja.md)を参照してください。
