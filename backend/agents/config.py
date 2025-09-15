"""
Configuration and shared utilities for the HIV PrEP Counselor system.
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables early
load_dotenv("../.env")

# CONFIGURATION
os.environ["TOKENIZERS_PARALLELISM"] = "false"


# Initialize OpenAI client
client = OpenAI()

# Default configuration
DEFAULT_CONFIG = {
    "model": "gpt-4o",
    "temperature": 0.7,
    "embedding_model": "text-embedding-3-small",
    "chunk_size": 500,
    "chunk_overlap": 50,
    "retrieval_k": 3,
    "max_rounds": 12,
    "recall_threshold": 2.5,
    "verbosity": 1
}

def get_api_key():
    """Get OpenAI API key from environment."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError(
            "API key not found. Please set OPENAI_API_KEY in your .env file."
        )
    return api_key


def get_llm_config(api_key: str, temperature: float = 0.7):
    """Create LLM configuration for agents."""
    config_list = [{
        "model": "gpt-4o",
        "api_key": api_key
    }]

    return {
        "config_list": config_list,
        "temperature": temperature
    }
