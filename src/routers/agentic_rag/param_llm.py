import os

from dotenv import load_dotenv
from langchain_ibm import ChatWatsonx
from langchain_openai import AzureChatOpenAI

load_dotenv()


def get_gpt_model():
    """
    Get the GPT model

    Returns:
      AzureChatOpenAI: model
    """

    WATSONX_GPT_OSS = os.getenv("WATSONX_GPT_OSS")
    if WATSONX_GPT_OSS == "True":
        # For watsonx gpt-oss
        WATSONX_MODEL_ID = os.getenv("WATSONX_MODEL_ID")
        WATSONX_API_KEY = os.getenv("WATSONX_API_KEY")
        WATSONX_BASE_URL = os.getenv("WATSONX_BASE_URL")
        WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")

        # LLMのパラメーター
        llm_params = {
            "frequency_penalty": 0,
            "max_tokens": 131072,
            "presence_penalty": 0,
            "temperature": 0,
            "top_p": 0.01,
        }

        model = ChatWatsonx(
            model_id=WATSONX_MODEL_ID,
            url=WATSONX_BASE_URL,
            apikey=WATSONX_API_KEY,
            project_id=WATSONX_PROJECT_ID,
            params=llm_params,
        )
    else:
        # Get the deployment name set in the environment variable
        CHAT_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT_NAME")
        AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
        OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
        OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION")

        AZURE_OPENAI_CHATGPT_DEPLOYMENT_NAME = os.getenv(
            "AZURE_OPENAI_CHATGPT_DEPLOYMENT_NAME"
        )

        deploy_name = AZURE_OPENAI_CHATGPT_DEPLOYMENT_NAME
        if deploy_name.startswith("o4-mini") or deploy_name.startswith("gpt-5"):
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
