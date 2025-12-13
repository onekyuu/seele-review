import os
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()
PORT = int(os.getenv("PORT", "8000"))
AI_MODEL = os.getenv("AI_MODEL", "gpt-3.5-turbo")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_BASE = os.getenv("GITHUB_API_BASE", "https://api.github.com")

GITLAB_WEBHOOK_SECRET = os.getenv("GITLAB_WEBHOOK_SECRET", "")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "")
GITLAB_API_BASE = os.getenv("GITLAB_API_BASE", "https://gitlab.com/api/v4")

NOTIFICATION_PLATFORM = os.getenv("NOTIFICATION_PLATFORM", "none")
NOTIFICATION_WEBHOOK_URL = os.getenv("NOTIFICATION_WEBHOOK_URL", "")

REPO_TARGETS = os.getenv("REPO_TARGETS", "gitlab")
REPO_REVIEW_LANG = os.getenv("REPO_REVIEW_LANG", "zh")

AI_COMMENT_MARKER = "<!-- powered by seele-review -->"


class Settings(BaseSettings):
    """
    Get settings from environment variables
    """
    defalut_ai_mode: str = "comment"
    debug: bool = True

    # Server Config
    port: int = Field(default=8000, description="Server Port")

    # AI Config
    openai_api_key: str = Field(
        default=OPENAI_API_KEY, description="OpenAI API KEY")
    ai_model: str = Field(default=AI_MODEL, description="AI Model")
    llm_base_url: str = Field(
        default=LLM_BASE_URL, description="LLM API Base URL"
    )

    # GitHub Config
    github_webhook_secret: str = Field(
        default=GITHUB_WEBHOOK_SECRET, description="GitHub Webhook Secret"
    )
    github_token: str = Field(
        default=GITHUB_TOKEN, description="GitHub Token")
    github_api_base: str = Field(
        default=GITHUB_API_BASE, description="GitHub API Base URL")

    # GitLab Config
    gitlab_webhook_secret: str = Field(
        default=GITLAB_WEBHOOK_SECRET, description="GitLab Webhook Secret"
    )
    gitlab_token: str = Field(default=GITLAB_TOKEN, description="GitLab Token")
    gitlab_api_base: str = Field(
        default=GITLAB_API_BASE, description="GitLab API Base URL"
    )
    gitlab_timeout: float = 10.0

    # notification Config
    notification_platform: str = Field(
        default=NOTIFICATION_PLATFORM, description="Notification Platform (none/slack/lark)"
    )
    notification_webhook_url: str = Field(
        default=NOTIFICATION_WEBHOOK_URL, description="Notification Webhook URL"
    )

    # CLI
    repo_targets: str = Field(
        default=REPO_TARGETS, description="Repository Targets for SEELE-Review"
    )
    repo_review_lang: Literal['zh', 'ja', 'en'] = Field(
        default=REPO_REVIEW_LANG, description="Review Language for SEELE-Review"
    )

    @property
    def seele_review_targets(self) -> list[str]:
        """the target platform for review results"""
        return [
            t.strip()
            for t in str(self.repo_targets).split(",")
            if t.strip()
        ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
