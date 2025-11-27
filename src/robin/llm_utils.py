from .config import OLLAMA_BASE_URL
from typing import Callable, Optional
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.callbacks.base import BaseCallbackHandler


class BufferedStreamingHandler(BaseCallbackHandler):
    def __init__(self, buffer_limit: int = 60, ui_callback: Optional[Callable[[str], None]] = None):
        self.buffer = ""
        self.buffer_limit = buffer_limit
        self.ui_callback = ui_callback

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.buffer += token
        if "\n" in token or len(self.buffer) >= self.buffer_limit:
            print(self.buffer, end="", flush=True)
            if self.ui_callback:
                self.ui_callback(self.buffer)
            self.buffer = ""

    def on_llm_end(self, response, **kwargs) -> None:
        if self.buffer:
            print(self.buffer, end="", flush=True)
            if self.ui_callback:
                self.ui_callback(self.buffer)
            self.buffer = ""


# --- Configuration Data ---
# Instantiate common dependencies once
_common_callbacks = [BufferedStreamingHandler(buffer_limit=60)]

# Define common parameters for most LLMs
_common_llm_params = {
    "temperature": 0,
    "streaming": True,
    "callbacks": _common_callbacks,
}

# Map input model choices (lowercased) to their configuration
# Each config includes the class and any model-specific constructor parameters
_llm_config_map = {
    'gpt4o': {
        'class': ChatOpenAI,
        'constructor_params': {'model_name': 'gpt-4o'},
        'required_env': ['OPENAI_API_KEY']
    },
    'gpt-4.1': {
        'class': ChatOpenAI,
        'constructor_params': {'model_name': 'gpt-4.1'},
        'required_env': ['OPENAI_API_KEY']
    },
    'claude-3-5-sonnet-latest': {
        'class': ChatAnthropic,
        'constructor_params': {'model': 'claude-3-5-sonnet-latest'},
        'required_env': ['ANTHROPIC_API_KEY']
    },
    'llama3.1': {
        'class': ChatOllama,
        'constructor_params': {'model': 'llama3.1:latest', 'base_url': OLLAMA_BASE_URL},
        'required_env': ['OLLAMA_BASE_URL']
    },
    'gemini-2.5-flash': {
        'class': ChatGoogleGenerativeAI,
        'constructor_params': {'model': 'gemini-2.5-flash'},
        'required_env': ['GOOGLE_API_KEY']
    },
    'gemini-2.5-flash-preview-09-2025': {
        'class': ChatGoogleGenerativeAI,
        'constructor_params': {'model': 'gemini-2.5-flash-preview-09-2025'},
        'required_env': ['GOOGLE_API_KEY']
    },
    'gemini-2.5-flash-lite': {
        'class': ChatGoogleGenerativeAI,
        'constructor_params': {'model': 'gemini-2.5-flash-lite'},
        'required_env': ['GOOGLE_API_KEY']
    }
}
