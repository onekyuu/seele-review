"""AI code review service main module."""
import os
import hmac
import hashlib
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request

load_dotenv()
PORT = int(os.getenv("PORT", "8000"))
AI_MODEL = os.getenv("AI_MODEL", "gpt-3.5-turbo")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

GITLAB_WEBHOOK_SECRET = os.getenv("GITLAB_WEBHOOK_SECRET", "")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "")
GITLAB_API_BASE = os.getenv("GITLAB_API_BASE", "https://gitlab.com/api/v4")

AI_COMMENT_MARKER = "<!-- powered by seele-review -->"

app = FastAPI(title="seele-review", version="1.0.0")


def _sign_github(body: bytes) -> str:
    mac = hmac.new(GITHUB_WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256)
    return "sha256=" + mac.hexdigest()


def _verify_github_signature(signature: Optional[str], raw_body: bytes):
    if not GITHUB_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=400, detail="Missing GITHUB_WEBHOOK_SECRET configuration")
    if signature is None:
        raise HTTPException(
            status_code=400, detail="Missing X-Hub-Signature-256 header")
    expected_signature = _sign_github(raw_body)
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=401, detail="Invalid GitHub signature")


def _verify_gitlab_signature(token: Optional[str]):
    if not GITLAB_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=400, detail="Missing GITLAB_WEBHOOK_SECRET configuration")
    if token is None:
        raise HTTPException(
            status_code=400, detail="Missing X-Gitlab-Token header")
    if token != GITLAB_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid GitLab token")


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: Optional[str] = Header(
        None, alias="X-Hub-Signature-256"),
):
    """github webhook endpoint"""
    raw_body = await request.body()
    print("Received GitHub event:", raw_body)
    _verify_github_signature(x_hub_signature_256, raw_body)


@app.post("/webhook/gitlab")
async def gitlab_webhook(
    request: Request,
    x_gitlab_event: Optional[str] = Header(None, alias="X-Gitlab-Event"),
    x_gitlab_token: Optional[str] = Header(None, alias="X-Gitlab-Token"),
):
    """gitlab webhook endpoint"""
    _verify_gitlab_signature(x_gitlab_token)
