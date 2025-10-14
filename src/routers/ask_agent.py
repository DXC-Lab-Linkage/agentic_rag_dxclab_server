"""Agentic RAG agent"""

import json
import logging
import os
import time
import traceback

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from src.routers.agentic_rag.message_utils import MsgUtils
from src.schemas.app_schemas import ChatModel

from .utils.constants import REST_API_500_ERROR
from .utils.csrf_utils import check_csrf
from .utils.log_dev import LogDev

load_dotenv()
log = LogDev()

msg_util = MsgUtils()
PY_FILE_NAME = "[src/routers/ask_agent.py]: "
router = APIRouter()
ENABLE_LOG_DEV = os.getenv("ENABLE_LOG_DEV")

# https://langchain-ai.github.io/langgraph/concepts/streaming/#streaming-graph-outputs-stream-and-astream
# https://langchain-ai.github.io/langgraph/how-tos/streaming-specific-nodes/


async def exec_graph(request: ChatModel, req: Request):
    """
    Execute graph of Langgraph

    Args:
      request (ChatModel): The current ChatModel object.
      request (Request): The current request object.
    Returns:
      answer: str
    """

    input_data = {
        "messages": [HumanMessage(content=request.user_request)],
        "turn": 1,
        "request": "",
        "rev_request": "",
        "plan": "",
        "plan_status": [],
        "plan_over": False,
        "plan_exec": "",
    }
    config = {"recursion_limit": 400, "configurable": {"thread_id": request.chat_id}}
    # Record the start time
    start_time = time.time()
    # Agent responds
    try:
        graph_app = req.app.state.graph_app
        answer = await graph_app.ainvoke(input_data, config=config)
    except Exception as err:
        print(err)
        raise Exception(err)
    # Record the end time of the process
    end_time = time.time()
    # Calculate elapsed time
    elapsed_time = end_time - start_time
    log.print("\n===== Final answer =====")
    log.print("-- **Conversation hisory** --")
    msg_history = msg_util.get_pure_msg(answer["messages"])
    log.print(msg_history)
    log.print("\n-- **Answer** --")
    latest_ai_msg = msg_util.get_latest_ai_tool_msg(answer["messages"])
    log.print(latest_ai_msg)
    log.print("-- Elapsed time --")
    log.print("{:.1f}".format(elapsed_time))
    return answer


async def exec_graph_stream(request: ChatModel, req: Request):
    """
    Execute graph of Langgraph in stream mode

    Args:
      request (ChatModel): The current ChatModel object.
      request (Request): The current request object.
    """

    input_data = {
        "messages": [HumanMessage(content=request.user_request)],
        "turn": 1,
        "request": "",
        "rev_request": "",
        "plan": "",
        "plan_status": [],
        "plan_over": False,
        "plan_exec": "",
    }

    config = {"recursion_limit": 400, "configurable": {"thread_id": request.chat_id}}
    start_time = time.time()
    # The complete message is stored at the end of the Streaming messages
    last_comp_message = ""
    try:
        graph_app = req.app.state.graph_app
        async for mode, chunk in graph_app.astream(
            input_data, config, stream_mode=["messages", "custom", "updates"]
        ):
            if mode == "messages":
                message, meta = chunk
                # Stream messages.
                langgraph_node = meta.get("langgraph_node")
                if (
                    langgraph_node == "create_final_answer"
                    or langgraph_node == "ans_llm_solo"
                    or langgraph_node == "ask_human"
                ):
                    if ENABLE_LOG_DEV == True:
                        print(message.content, end="", flush=True)
                    data = {"type": "msg", "content": message.content}
                    yield f"{json.dumps(data)}\n\n"
            elif mode == "updates":
                pass
            elif mode == "custom":
                custom_event = chunk
                data = {"type": "custom", "content": custom_event}
                yield f"{json.dumps(data)}\n\n"
        # Get the complete message stored at the end of messages
        last_comp_message = message.content[1:-1]
        sanitized_answer = last_comp_message
        data = {"type": "final_msg", "content": sanitized_answer}
        yield f"{json.dumps(data)}\n\n"
    except Exception as err:
        full_traceback = traceback.format_exc()
        print("=" * 80)
        print("FULL ERROR TRACEBACK:")
        print(full_traceback)
        print("=" * 80)
        print(f"Error type: {type(err).__name__}")
        print(f"Error message: {err}")

        data = {
            "type": "error",
            "content": "Error: An error occurred while running the Agent.",
            "detail": str(err),
            "traceback": full_traceback,
        }
        yield f"{json.dumps(data)}\n\n"
        raise Exception(err)
    end_time = time.time()
    elapsed_time = end_time - start_time
    log.print("\n-- Elapsed time --")
    elapsed_str = f"Elapsed time:" + "{:.1f}".format(elapsed_time) + "(s)"
    log.print(elapsed_str)
    data = {"type": "custom", "content": elapsed_str}
    yield f"{json.dumps(data)}\n\n"


@router.post("/api/ask_agent")
async def ask_agent(request: ChatModel, req: Request):
    try:
        check_csrf(req)
    except Exception as err:
        print(f"{PY_FILE_NAME}{err}")
        raise err
    try:
        # No "await" because of an asynchronous generator.
        generator = exec_graph_stream(request, req)
        return StreamingResponse(generator, media_type="text/event-stream")
    except Exception as err:
        logging.error(f"Error: [/api/ask_agent] {err} Internal server error.")
        raise HTTPException(status_code=500, detail=REST_API_500_ERROR)
