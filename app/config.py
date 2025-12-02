from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    defalut_ai_mode: str = "comment"
    debug: bool = True

    # Server Config
    port: int = Field(default=8000, description="服务端口")

    # AI Config
    qwen_api_key: str = Field(default="", description="通义千问 API Key")
    ai_model: Literal["gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"] = Field(
        default="gpt-4o-mini", description="AI 模型"
    )

    # GitHub Config
    github_webhook_secret: str = Field(default="", description="GitHub Webhook 密钥")
    github_token: str = Field(default="", description="GitHub Token")

    # GitLab Config
    gitlab_webhook_secret: str = Field(default="", description="GitLab Webhook 密钥")
    gitlab_token: str = Field(default="", description="GitLab Token")
    gitlab_api_base: str = Field(
        default="https://gitlab.com/api/v4", description="GitLab API 基础 URL"
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
