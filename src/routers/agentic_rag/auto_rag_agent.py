import json
import os
import time
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import InjectedState, ToolNode
from langgraph.types import StreamWriter
from pydantic.errors import PydanticInvalidForJsonSchema

from src.routers.agentic_rag.answer_llm import AnswerLlmAgent
from src.routers.agentic_rag.ask_human import AskHumanAgent
from src.routers.agentic_rag.auto_research import AutoResearchAgent, tool_info
from src.routers.agentic_rag.message_utils import MsgUtils
from src.routers.agentic_rag.param_llm import get_gpt_model
from src.routers.agentic_rag.router_agent import RouterAgent
from src.routers.agentic_rag.state import State
from src.routers.utils.agent_msg_manager import AgentMsgManager
from src.routers.utils.log_dev import LogDev
from src.routers.utils.prompt_manager import PromptManager

log = LogDev()
load_dotenv()

agent_msg_mgr = AgentMsgManager()
prompt_mgr = PromptManager()
msg_util = MsgUtils()

# LangSmith
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT")


class AutoRagAgent:
    """
    AutoRagAgent
    Autonomously creates plans and conducts research using RAG and web searches
    """

    def __init__(self):
        self._rt = RouterAgent()
        self._al = AnswerLlmAgent()
        self._ar = AutoResearchAgent()
        self._ah = AskHumanAgent()
        self._tools = [
            self._ar.ans_tavily,
            self._ar.ans_arxiv,
            self._ar.ans_llm_base,
            self._ar.search_rag,
        ]

    def _extract_plan(self, state: State) -> str:
        """
        Get the first incomplete plan from the plans created on create_plan

        Args:
          state: MessagesState

        Returns:
          str: plan
        """
        log.print("\n<<Start: extract_plan>>")
        # Get the first incomplete plan
        if state["plan_status"] is None:
            msg = "Error: plan_status does not exist."
            print(msg)
            raise ValueError(msg)
        # Process to obtain plan based on index information
        # Get the first index where plan_status is 'open'
        index = next(
            (i for i, status in enumerate(state["plan_status"]) if status == "open"),
            None,
        )
        if index is not None:
            log.print("Plan no.:" + str(index))
            pass
        else:
            msg = "Error: No elements with plan_status 'open' is found."
            raise ValueError(msg)
        plan_js = state["plan"]
        plan_arr = plan_js["plan"]
        plan = plan_arr[index]
        return plan

    def extract_tool_name_from_content(self, response):
        """
        Extract tool name from content
        """
        try:
            if hasattr(response, "tool_calls") and response.tool_calls:
                return msg_util.get_tool_names(response)

            content = response.content
            if not content:
                return None

            # Parse as JSON.
            data = json.loads(content)

            # Extract recipient_name from tool_uses
            if "tool_uses" in data and data["tool_uses"]:
                tool_use = data["tool_uses"][0]
                recipient_name = tool_use.get("recipient_name", "")

                # Extract tool name from functions.[tool_name]
                if "." in recipient_name:
                    tool_name = recipient_name.split(".")[-1]
                else:
                    tool_name = recipient_name

                return [tool_name] if tool_name else None

        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            print(f"Error extracting tool name: {e}")
            return None

        return None

    def _select_tool(
        self,
        state: Annotated[State, InjectedState],
        config: RunnableConfig,
        writer: StreamWriter,
    ) -> dict:
        """
        Select the tool to call with Function calling
        the user asks questions like "What does XYZ mean?" or other queries based on general knowledge.

        Args:
          state: State:
          config: RunnableConfig

        Returns:
          dict: messages
        """
        log.print("\n<<Start: select_tool>>")
        # Extract a plan to execute
        plan = self._extract_plan(state)
        plan_exec = {"plan_exec": plan}
        model = get_gpt_model()
        max_retries = 1

        for attempt in range(max_retries + 1):
            try:
                chain = model.bind_tools(self._tools)
                break  # Exit the loop if the execution is successful
            except PydanticInvalidForJsonSchema as e:
                if attempt == max_retries:
                    # Rethrow exception if maximum retry count is reached
                    raise e
                else:
                    # Optionally, insert a short wait before retrying
                    print(
                        f"Select the tool to call(bind): Attempt {attempt + 1} failed, retrying..."
                    )
                    time.sleep(1)  # Adjust the wait time as needed

        for attempt in range(max_retries + 1):
            prompt_template = prompt_mgr.get_prompt("select_tool")
            prompt = prompt_template.format(plan=plan, tool_info=tool_info)
            response = chain.invoke(
                prompt, config={**config, "tool_choice": "required"}
            )

            tool_name = msg_util.get_tool_names(response)

            if not tool_name:
                tool_name = self.extract_tool_name_from_content(response)

            if tool_name:
                break
            else:
                print(
                    f"Select the tool to call(invoke): Attempt {attempt + 1} failed. Retrying..."
                )
                print(f"Response: {response}")
        else:
            print("Warning: Even after retries, tool_name could not be obtained.")
            tool_name = ["N/A"]

        msg = agent_msg_mgr.get_msg("select_tool", plan=plan, tool_name=tool_name)
        log.print(msg + "\n")
        writer(msg)

        return {"messages": [response], "plan_exec": plan_exec}

    async def create_graph(self):
        """
        Create a graph of LangGraph

        Returns:
          CompiledStateGraph: app
        """
        try:
            tool_node = ToolNode(self._tools)
            # ---- Define the Graph ----
            workflow = StateGraph(state_schema=State)

            # ---- Define the node. ----
            # -- Parent Agent --
            # Decide which of ans_llm_solo, create_plan, or ask_human you want to execute and use Command to transition.
            workflow.add_node("route_request", self._rt.route_request)
            # -- Answer solo agent.(Answer solo with llm base knowledge) --
            workflow.add_node("ans_llm_solo", self._al.ans_llm_solo)
            # -- Ask human agent. --
            workflow.add_node("ask_human", self._ah.ask_human)
            # -- Auto Research Agent --
            workflow.add_node("create_plan", self._ar.create_plan)
            workflow.add_node("select_tool", self._select_tool)
            workflow.add_node("call_tool", tool_node)
            workflow.add_node("update_plan_status", self._ar.update_plan_status)
            workflow.add_node("judge_replan", self._ar.judge_replan)
            workflow.add_node("create_final_answer", self._ar.create_final_answer)
            workflow.add_node("create_revised_plan", self._ar.create_revised_plan)

            # --- Define the edge. ---
            # -- Route_request --
            workflow.add_edge(START, "route_request")
            # -- Answer llm solo --
            workflow.add_edge("ans_llm_solo", END)
            # -- Ask human --
            workflow.add_edge("ask_human", END)
            # -- Auto research --
            workflow.add_edge("create_plan", "select_tool")
            workflow.add_edge("select_tool", "call_tool")
            # There is a process to detect errors that occur in the tool at the first process of node:update_plan_status
            workflow.add_edge("call_tool", "update_plan_status")
            workflow.add_edge("create_revised_plan", "select_tool")

            # --- Conditional Edges ---
            workflow.add_conditional_edges(
                "update_plan_status",  # Node executed before the judgment
                self._ar.check_open_plan,  # Check by check_open_plan
                # True: A plan with the plan status open exists, False: A plan does not exist
                # If False, create a response for the user
                {True: "select_tool", False: "judge_replan"},
            )
            # Add simple in-memory checkpointer
            memory = MemorySaver()
            app = workflow.compile(checkpointer=memory)
            return app
        except Exception as err:
            print(err)
            raise Exception(err)
