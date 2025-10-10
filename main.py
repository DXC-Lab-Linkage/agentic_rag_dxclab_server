"""The main program that runs when the app starts.
Configures the router, sessions.
"""

import json
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from src.routers.agentic_rag.auto_rag_agent import AutoRagAgent
from src.routers.ask_agent import router as ask_agent
from src.routers.get_chat_id import router as chat_id
from src.routers.get_csrf import router as get_csrf
from src.routers.get_param import router as get_param
from src.routers.start_chat import router as start_chat

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ar = AutoRagAgent()
    app.state.graph_app = await ar.create_graph()
    yield


# Since for production use, the settings will not display specifications, etc.
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv(
        "SESSION_SECRET_KEY",
    ),
    same_site="Strict",
    https_only=True,
)


# CSP
class CspMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self';"
            "style-src 'self' ;"
            "style-src-elem 'self' https://fonts.googleapis.com 'sha256-47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=' 'sha256-HcB32D63QxbHF81G9ir4A4ZtfSFlntT1ZUYUPKNuzfI=';"
            "font-src 'self' https://fonts.gstatic.com;"
            "script-src 'self' 'unsafe-inline';"
            "img-src 'self';"
            "frame-src 'self';"
            "connect-src 'self';"
        )
        return response


# --- CORS setting---
# Allowed origins (your site URL)
CORS_ORIGINS = json.loads(os.getenv("CORS_ORIGINS"))
origins = [CORS_ORIGINS]

# Allowed Headers
allowed_headers = ["Content-Type", "X-CSRF-TOKEN"]

# Adding CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Specify the origins to allow
    # Specify which HTTP methods are allowed (e.g. GET and POST)
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=allowed_headers,  # Specify allowed HTTP headers
)

app.add_middleware(CspMiddleware)

app.include_router(get_param)
app.include_router(chat_id)
app.include_router(get_csrf)
app.include_router(start_chat)
app.include_router(ask_agent)


WATSONX_GPT_OSS = os.getenv("WATSONX_GPT_OSS")
if WATSONX_GPT_OSS == "True":
    print(" LLM: watsonx gpt-oss.")

if os.path.exists("dist"):
    # If you mount dist/, you will get a 404 when accessing the Vue Router path. So you should not mount it.
    app.mount("/assets", StaticFiles(directory="dist/assets", html=True), name="assets")

# Vue Router Support


@app.get("/{catchall:path}", response_class=HTMLResponse)
def catch_all():
    return HTMLResponse(open("./dist/index.html").read())


# Reference: Starlette session middleware: https://www.starlette.io/middleware/#sessionmiddleware
