from __future__ import annotations
import hmac
import hashlib
import json
import os
from typing import Dict, Any, List, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# ------------------ 环境变量 ------------------
# 自动读取 .env 文件，便于本地调试
load_dotenv()

# ------------------ 配置 ------------------
PORT = int(os.getenv("PORT", 8000))
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# GitHub 配置
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# GitLab 配置
GITLAB_WEBHOOK_SECRET = os.getenv("GITLAB_WEBHOOK_SECRET", "")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "")
GITLAB_API_BASE = os.getenv("GITLAB_API_BASE", "https://gitlab.com/api/v4")

# 评论标记，用于避免重复创建评论（会更新已有的 AI 评论）
AI_COMMENT_MARKER = "<!-- ai-review:git-mr-ai-reviewer -->"

# 初始化 FastAPI 应用
app = FastAPI(title="git-mr-ai-reviewer")

# ============================================================
# 工具方法：用于验证签名 / 调用 AI / 格式化评论
# ============================================================


def _sign_github(body: bytes) -> str:
    """根据 body 和 secret 计算 GitHub 签名（sha256）"""
    mac = hmac.new(GITHUB_WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256)
    return "sha256=" + mac.hexdigest()


def _verify_github_signature(sig_header: Optional[str], raw_body: bytes) -> None:
    """校验 GitHub Webhook 请求签名，确保请求来自 GitHub"""
    if not GITHUB_WEBHOOK_SECRET:  # 如果没配置 secret，就跳过校验（生产环境不推荐）
        return
    if not sig_header:
        raise HTTPException(
            status_code=401, detail="Missing X-Hub-Signature-256")
    expected = _sign_github(raw_body)
    if not hmac.compare_digest(expected, sig_header):
        raise HTTPException(status_code=401, detail="Bad signature")


def _verify_gitlab_token(token_header: Optional[str]) -> None:
    """校验 GitLab Webhook 的 Token"""
    if not GITLAB_WEBHOOK_SECRET:
        return
    if not token_header or token_header != GITLAB_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Bad X-Gitlab-Token")


async def _ai_review_summary(repo: str, title: str, description: str, changes: List[Dict[str, Any]]) -> str:
    """
    调用 AI 生成代码评审结果
    - repo: 仓库名
    - title: PR/MR 标题
    - description: PR/MR 描述
    - changes: 文件变更列表（含 diff）
    """
    # 如果没配置 OPENAI_API_KEY，就返回一个静态提示
    if not OPENAI_API_KEY:
        return (
            "### 🤖 AI Review (offline)\n"
            "- 检查是否包含单元测试\n"
            "- 公共方法是否有 docstring\n"
            "- 注意边界条件与异常处理\n"
            "- 安全性：参数校验/日志脱敏\n"
            f"{AI_COMMENT_MARKER}"
        )

    # 限制 diff 内容大小，避免 prompt 太长
    max_patch_chars = 6000
    diff_chunks, budget = [], max_patch_chars
    for ch in changes:
        patch = ch.get("patch") or ch.get("diff") or ""
        if not patch:
            continue
        snippet = patch[: min(budget, len(patch))]
        diff_chunks.append(
            f"\n\n# File: {ch.get('filename') or ch.get('new_path')}\n{snippet}")
        budget -= len(snippet)
        if budget <= 0:
            break

    # AI 提示词
    system = (
        "You are a seasoned staff engineer performing code review. "
        "Focus on correctness, security, performance, readability, tests, and edge cases. "
        "Be concise but actionable."
    )
    user = (
        f"Repository: {repo}\n"
        f"Title: {title}\n"
        f"Description: {description or '(no description)'}\n"
        f"Provide a prioritized review with fixes and checklists."
        f"{''.join(diff_chunks)}"
    )

    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}",
               "Content-Type": "application/json"}
    payload = {
        "model": AI_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.2,
    }

    # 调用 OpenAI API
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()

    return f"### 🤖 AI Review\n\n{content}\n\n{AI_COMMENT_MARKER}"

# ============================================================
# GitHub 相关逻辑：拉取 PR diff、提交评论
# ============================================================


async def _github_fetch_pr_changes(owner: str, repo: str, number: int):
    """获取 GitHub PR 的改动文件和 PR 信息"""
    base = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}",
               "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient(timeout=30) as client:
        pr = (await client.get(f"{base}/pulls/{number}", headers=headers)).json()
        files = (await client.get(f"{base}/pulls/{number}/files?per_page=100", headers=headers)).json()

    changes = [{"filename": f.get("filename"), "status": f.get(
        "status"), "patch": f.get("patch", "")} for f in files]
    return changes, pr


async def _github_upsert_review_comment(owner: str, repo: str, number: int, body: str):
    """在 GitHub PR 下添加或更新 AI 评论"""
    base = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}",
               "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient(timeout=30) as client:
        comments = (await client.get(f"{base}/issues/{number}/comments?per_page=100", headers=headers)).json()
        existing = next(
            (c for c in comments if AI_COMMENT_MARKER in (c.get("body") or "")), None)

        if existing:
            # 更新已有评论
            await client.patch(f"{base}/issues/comments/{existing['id']}", headers=headers, json={"body": body})
        else:
            # 新建评论
            await client.post(f"{base}/issues/{number}/comments", headers=headers, json={"body": body})


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: Optional[str] = Header(
        None, alias="X-Hub-Signature-256"),
):
    """处理 GitHub Webhook：只关心 PR 相关事件"""
    raw = await request.body()
    _verify_github_signature(x_hub_signature_256, raw)

    payload = json.loads(raw.decode("utf-8"))
    if x_github_event != "pull_request":
        return JSONResponse({"ok": True, "skipped": f"event {x_github_event}"})

    action = payload.get("action")
    if action not in {"opened", "synchronize", "reopened", "ready_for_review"}:
        return JSONResponse({"ok": True, "skipped": f"action {action}"})

    pr = payload.get("pull_request", {})
    if pr.get("draft"):  # 跳过草稿 PR
        return JSONResponse({"ok": True, "skipped": "draft PR"})

    owner, repo = payload["repository"]["full_name"].split("/")
    number = pr["number"]

    # 获取改动 & 调用 AI
    changes, pr_obj = await _github_fetch_pr_changes(owner, repo, number)
    review = await _ai_review_summary(payload["repository"]["full_name"], pr_obj.get("title", ""), pr_obj.get("body", ""), changes)
    await _github_upsert_review_comment(owner, repo, number, review)

    return {"ok": True, "reviewed": True}

# ============================================================
# GitLab 相关逻辑：拉取 MR diff、提交评论
# ============================================================


async def _gitlab_fetch_mr_changes(project_id: int, iid: int):
    """获取 GitLab MR 改动文件和 MR 信息"""
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    async with httpx.AsyncClient(timeout=30) as client:
        mr = (await client.get(f"{GITLAB_API_BASE}/projects/{project_id}/merge_requests/{iid}", headers=headers)).json()
        changes = (await client.get(f"{GITLAB_API_BASE}/projects/{project_id}/merge_requests/{iid}/changes", headers=headers)).json()["changes"]

    normalized = []
    for f in changes:
        status = "modified"
        if f.get("new_file"):
            status = "added"
        elif f.get("deleted_file"):
            status = "removed"
        elif f.get("renamed_file"):
            status = "renamed"
        normalized.append({"filename": f.get("new_path") or f.get(
            "old_path"), "status": status, "patch": f.get("diff", "")})
    return normalized, mr


async def _gitlab_upsert_note(project_id: int, iid: int, body: str):
    """在 GitLab MR 下添加或更新 AI 评论"""
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    async with httpx.AsyncClient(timeout=30) as client:
        notes = (await client.get(f"{GITLAB_API_BASE}/projects/{project_id}/merge_requests/{iid}/notes?per_page=100", headers=headers)).json()
        existing = next(
            (n for n in notes if AI_COMMENT_MARKER in (n.get("body") or "")), None)

        if existing:
            await client.put(f"{GITLAB_API_BASE}/projects/{project_id}/merge_requests/{iid}/notes/{existing['id']}", headers=headers, json={"body": body})
        else:
            await client.post(f"{GITLAB_API_BASE}/projects/{project_id}/merge_requests/{iid}/notes", headers=headers, json={"body": body})


@app.post("/webhook/gitlab")
async def gitlab_webhook(request: Request, x_gitlab_token: Optional[str] = Header(None, alias="X-Gitlab-Token")):
    """处理 GitLab Webhook：只关心 MR 事件"""
    raw = await request.body()
    _verify_gitlab_token(x_gitlab_token)

    payload = json.loads(raw.decode("utf-8"))
    if payload.get("object_kind") != "merge_request":
        return JSONResponse({"ok": True, "skipped": f"kind {payload.get('object_kind')}"})

    attrs = payload.get("object_attributes", {})
    action, state, title = attrs.get("action"), attrs.get(
        "state"), attrs.get("title", "")
    if action not in {"open", "reopen", "update"} or state not in {"opened", "open"}:
        return JSONResponse({"ok": True, "skipped": f"action/state {action}/{state}"})
    if attrs.get("work_in_progress") or title.lower().startswith(("wip", "draft")):
        return JSONResponse({"ok": True, "skipped": "draft/WIP"})

    changes, mr_obj = await _gitlab_fetch_mr_changes(payload["project"]["id"], attrs["iid"])
    review = await _ai_review_summary(f"gitlab:{payload['project']['path_with_namespace']}", title, mr_obj.get("description", ""), changes)
    await _gitlab_upsert_note(payload["project"]["id"], attrs["iid"], review)

    return {"ok": True, "reviewed": True}

# ============================================================
# 健康检查 & 本地启动
# ============================================================


@app.get("/healthz")
async def healthz():
    """健康检查接口，用于运维探活"""
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
