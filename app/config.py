import os
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()
PORT = int(os.getenv("PORT", "8000"))
AI_MODEL = os.getenv("AI_MODEL", "gpt-3.5-turbo")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "")

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GITHUB_API_TOKEN = os.getenv("GITHUB_API_TOKEN", "")

GITLAB_WEBHOOK_SECRET = os.getenv("GITLAB_WEBHOOK_SECRET", "")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "")
GITLAB_API_BASE = os.getenv("GITLAB_API_BASE", "https://gitlab.com/api/v4")

AI_COMMENT_MARKER = "<!-- powered by seele-review -->"


class Settings(BaseSettings):
    defalut_ai_mode: str = "comment"
    debug: bool = True

    # Server Config
    port: int = Field(default=8000, description="Server Port")

    # AI Config
    qwen_api_key: str = Field(default=QWEN_API_KEY, description="Qwen API KEY")
    ai_model: str = Field(default=AI_MODEL, description="AI Model")

    # GitHub Config
    github_webhook_secret: str = Field(
        default=GITHUB_WEBHOOK_SECRET, description="GitHub Webhook Secret"
    )
    github_api_token: str = Field(default=GITHUB_API_TOKEN, description="GitHub Token")

    # GitLab Config
    gitlab_webhook_secret: str = Field(
        default=GITLAB_WEBHOOK_SECRET, description="GitLab Webhook Secret"
    )
    gitlab_token: str = Field(default=GITLAB_TOKEN, description="GitLab Token")
    gitlab_api_base: str = Field(
        default=GITLAB_API_BASE, description="GitLab API Base URL"
    )
    gitlab_timeout: float = 10.0

    # Slack Config
    slack_webhook_ai_review: str = Field(default="", description="Slack Webhook URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
