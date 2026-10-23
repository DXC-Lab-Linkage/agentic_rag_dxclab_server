"""Generate chat_id and send it from backend to frontend"""

from uuid import uuid4

from dotenv import load_dotenv
from fastapi import APIRouter, Request

from ..schemas.app_schemas import ChatId
from .utils.constants import MAX_SESSION_CHAT_IDS
from .utils.csrf_utils import check_csrf

load_dotenv()
PY_FILE_NAME = "[src/routers/get_chat_id.py]: "
router = APIRouter()


@router.post("/api/get_chat_id")
def get_parameters(req: Request):
    """
    Generates a unique Chat ID and returns it as a ChatId schema object.

    This endpoint is called when the chat screen is opened and assigns a unique
    Chat ID. The generated Chat ID is used as a key to track and manage the chat conversation state.

    A unique Chat ID is assigned when the chat screen is opened. This ID is managed until the chat screen is closed, reloaded. This Chat ID is used as the key for the action log, so you can check the user's behavior by referring to the log. This is important information that will be the DB key, so it is generated in the backend.

    Parameters:
      req (Request): FastAPI Request object

    Returns:
      ChatId: ChatId schema object containing the newly generated Chat ID
    """
    try:
        check_csrf(req)
    except Exception as err:
        print(f"{PY_FILE_NAME}{err}")
        raise err
    chat_id = str(uuid4())
    # Store the issued chat_id in the session so that ask_agent can verify it.
    # Keep a list to support multiple tabs and reloads.
    chat_ids = req.session.get("chat_ids", [])
    chat_ids.append(chat_id)
    req.session["chat_ids"] = chat_ids[-MAX_SESSION_CHAT_IDS:]
    ret = ChatId(
        chat_id=chat_id,
    )
    return ret
