import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
