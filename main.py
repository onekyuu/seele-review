"""AI code review service main module."""
import os
import hmac
import hashlib
import json
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
import httpx
from openai import OpenAI
from fastapi.responses import JSONResponse

load_dotenv()
PORT = int(os.getenv("PORT", "8000"))
AI_MODEL = os.getenv("AI_MODEL", "gpt-3.5-turbo")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "")

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GITHUB_API_TOKEN = os.getenv("GITHUB_API_TOKEN", "")

GITLAB_WEBHOOK_SECRET = os.getenv("GITLAB_WEBHOOK_SECRET", "")
GITLAB_API_TOKEN = os.getenv("GITLAB_API_TOKEN", "")
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


async def _get_gitlab_mr_diff(
    project_id: int, iid: int, api_token: Optional[str] = None
):
    """Get GitLab merge request diff"""
    token = api_token or GITLAB_API_TOKEN
    headers = {"PRIVATE-TOKEN": token} if token else {}
    async with httpx.AsyncClient(timeout=30) as client:
        mr_resp = await client.get(
            f"{GITLAB_API_BASE}/projects/{project_id}/merge_requests/{iid}",
            headers=headers,
        )
        mr_resp.raise_for_status()
        mr_obj = mr_resp.json()

        diff_resp = await client.get(
            f"{GITLAB_API_BASE}/projects/{project_id}/merge_requests/{iid}/changes",
            headers=headers,
        )
        diff_resp.raise_for_status()
        diff_obj = diff_resp.json().get("changes", [])

    normalized_diff: List[Dict[str, Any]] = []
    for f in diff_obj:
        status = "modified"
        if f.get("new_file"):
            status = "added"
        elif f.get("deleted_file"):
            status = "deleted"
        elif f.get("renamed_file"):
            status = "renamed"
        normalized_diff.append(
            {
                "filename": f.get("new_path", "") or f.get("old_path"),
                "status": status,
                "patch": f.get("diff", ""),
            }
        )

    return normalized_diff, mr_obj


def filter_no_code_file(changes):
    """Gitlab merge request file filter"""
    code_file_suffix = ["ts", "js", "tsx", "jsx", "vue", "css", "py"]
    filtered = []
    for change in changes:
        new_path = change.get("filename") or change.get("new_path", "")
        suffix = new_path.split(".")[-1].lower()
        if suffix in code_file_suffix:
            filtered.append(change)
    return filtered


@app.post("/webhook/gitlab")
async def gitlab_webhook(
    request: Request,
    x_gitlab_event: Optional[str] = Header(None, alias="X-Gitlab-Event"),
    x_ai_mode: Optional[str] = Header(None, alias="X-Ai-Mode"),
    x_push_url: Optional[str] = Header(None, alias="X-Push-Url"),
    x_gitlab_token: Optional[str] = Header(None, alias="X-Gitlab-Token"),
):
    """gitlab webhook endpoint"""
    print("Received Request body:\n", await request.body())
    print("Received GitLab event:\n", x_gitlab_event)
    print("Received AI mode:\n", x_ai_mode)
    print("Received Push URL:\n", x_push_url)
    _verify_gitlab_signature(x_gitlab_token)
    raw = await request.body()

    try:
        payload = json.loads(raw.decode("utf-8"))
        print("Parsed GitLab payload:\n", payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if payload.get("object_kind") != "merge_request":
        return JSONResponse({"ok": True, "skipped": f"kind {payload.get("object_kind")}"})

    attrs = payload.get("object_attributes", {})
    action = attrs.get("action")
    state = attrs.get("state")
    title = attrs.get("title", "") or ""

    if action not in {"open", "reopen", "update"} or state not in {"opened", "open"}:
        return JSONResponse({"ok": True, "skipped": f"action/state {action}/{state}"})

    if attrs.get("work_in_progress") or title.lower().startswith(("wip", "draft")):
        return JSONResponse({"ok": True, "skipped": "draft/WIP"})

    project_id = payload.get("project", {}).get("id")
    iid = attrs.get("iid")

    if not (project_id and iid):
        raise HTTPException(
            status_code=400, detail="Missing project_id or iid")

    ai_mode = (x_ai_mode or "comment").lower()
    if ai_mode not in ("comment", "report"):
        ai_mode = "comment"

    push_url = x_push_url or ""
    api_token = GITLAB_API_TOKEN or None

    diff, mr_obj = await _get_gitlab_mr_diff(project_id, iid, api_token=api_token)
    desc = mr_obj.get("description", "") or ""
    repo_label = f"gitlab:{payload.get('project', {}).get('path_with_namespace', project_id)}"

    print(
        f"Processing GitLab MR !{iid} in project {project_id} with AI mode {ai_mode}")
    print(f"MR Diff:\n{diff}")
    print(f"MR OBJ:\n{mr_obj}")
