import os

from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()


def get_gpt_model():
    """
    Get the GPT model

    Returns:
      AzureChatOpenAI: model
    """
    # Get the deployment name set in the environment variable
    CHAT_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT_NAME")
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION")

    AZURE_OPENAI_CHATGPT_DEPLOYMENT_NAME = os.getenv(
        "AZURE_OPENAI_CHATGPT_DEPLOYMENT_NAME"
    )

    if AZURE_OPENAI_CHATGPT_DEPLOYMENT_NAME == "o4-mini":
        model = AzureChatOpenAI(
            azure_deployment=CHAT_DEPLOYMENT_NAME,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            openai_api_key=OPENAI_API_KEY,
            openai_api_version=OPENAI_API_VERSION,
            request_timeout=300,
            streaming=True,
            model_kwargs={
                "max_completion_tokens": 16384,
            },
        )
    else:
        model = AzureChatOpenAI(
            deployment_name=CHAT_DEPLOYMENT_NAME,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            openai_api_key=OPENAI_API_KEY,
            openai_api_version=OPENAI_API_VERSION,
            request_timeout=300,
            temperature=0,
            logprobs=None,
            max_tokens=16384,
            streaming=True,
        )
    return model
