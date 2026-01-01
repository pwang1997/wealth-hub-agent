import os

from dotenv import load_dotenv

load_dotenv()


class AgentModelConfig:
    OPENAI_MODEL = "gpt-5-mini-2025-08-07"
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
