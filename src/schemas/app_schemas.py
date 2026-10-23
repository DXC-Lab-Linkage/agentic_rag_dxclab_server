from datetime import datetime
from typing import Literal, Union

from pydantic import BaseModel, Field

from src.routers.utils.constants import MAX_CHAT_ID_LENGTH, MAX_USER_REQUEST_LENGTH


class UserInfo(BaseModel):
    user_id: str = Field(..., title="User id")


class CsrfToken(BaseModel):
    csrf_token: str = Field(..., title="CSRF token")


class Parameters(BaseModel):
    FRONT_MSG_LANG: str = Field(
        ..., title="Language of front-end message(EN: English, JA: Japanese)"
    )


class ChatId(BaseModel):
    chat_id: str = Field(..., title="Chat id")


class StartChat(BaseModel):
    chat_start_date: Union[datetime, Literal[""]] = Field(
        "", title="Chat start date and time"
    )


class UserModel(BaseModel):
    user_id: str = Field(..., title="User id")
    password: str = Field(..., title="Password")


class ChatModel(BaseModel):
    chat_id: str = Field(
        ...,
        max_length=MAX_CHAT_ID_LENGTH,
        title="Chat id assigned to a series of conversations",
    )
    user_request: str = Field(
        ..., max_length=MAX_USER_REQUEST_LENGTH, title="User request or question"
    )
    answer: str = Field(..., title="Answer of LLM")
    chat_start_date: Union[datetime, str] = Field("", title="Chat start date and time")
