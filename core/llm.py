from langchain_openai import ChatOpenAI

from config.settings import (
    DEFAULT_MODEL,
    MAX_RETRIES,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    REQUEST_TIMEOUT,
)


def build_llm_with_tools(tools):
    llm = ChatOpenAI(
        model=DEFAULT_MODEL,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
        max_retries=MAX_RETRIES,
        timeout=REQUEST_TIMEOUT,
    )
    return llm.bind_tools(tools)
