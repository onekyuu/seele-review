from __future__ import annotations

import hmac
import hashlib
import json
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# 读取 .env 文件，便于本地开发
load_dotenv()

# ------------------ 基础配置 ------------------
PORT = int(os.getenv("PORT", 8000))

# AI 配置
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# GitHub 配置
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# GitLab 配置
GITLAB_WEBHOOK_SECRET = os.getenv("GITLAB_WEBHOOK_SECRET", "")
# 默认 API Token，可以被 X-Gitlab-Api-Token 覆盖
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "")
GITLAB_API_BASE = os.getenv("GITLAB_API_BASE", "https://gitlab.com/api/v4")

# AI 评论标记，用于幂等更新
AI_COMMENT_MARKER = "<!-- ai-review:git-mr-ai-reviewer -->"

app = FastAPI(title="git-mr-ai-reviewer")


# ============================================================
# 工具函数：签名校验、AI 调用、机器人推送
# ============================================================

def _sign_github(body: bytes) -> str:
    """根据 body 和 secret 计算 GitHub 签名（sha256）"""
    mac = hmac.new(GITHUB_WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256)
    return "sha256=" + mac.hexdigest()


def _verify_github_signature(sig_header: Optional[str], raw_body: bytes) -> None:
    """校验 GitHub Webhook 请求签名，确保请求来自 GitHub"""
    if not GITHUB_WEBHOOK_SECRET:
        # 未配置 secret 时，跳过校验（生产环境不推荐）
        return
    if not sig_header:
        raise HTTPException(
            status_code=401, detail="Missing X-Hub-Signature-256")

    expected = _sign_github(raw_body)
    if not hmac.compare_digest(expected, sig_header):
        raise HTTPException(
            status_code=401, detail="Bad GitHub webhook signature")


def _verify_gitlab_token(token_header: Optional[str]) -> None:
    """
    校验 GitLab Webhook Secret。
    GitLab 会把 Webhook 页面中的 Secret token 放到 X-Gitlab-Token 头里。
    """
    if not GITLAB_WEBHOOK_SECRET:
        # 未配置时允许通过（测试环境可以，生产建议必须配置）
        return
    if not token_header or token_header != GITLAB_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Bad X-Gitlab-Token")


async def _ai_review_summary(
    repo: str,
    title: str,
    description: str,
    changes: List[Dict[str, Any]],
    mode: str = "comment",
) -> str:
    """
    调用 AI 生成代码评审结果。

    mode:
      - "comment": 偏短的点评风格，适合作为 PR / MR 下的一条评论
      - "report": 结构化报告风格，适合作为较长的评审说明
    """
    # 没有 API key 时，返回一个本地静态提示，避免整个流程失败
    if not OPENAI_API_KEY:
        offline = (
            "### 🤖 AI Review (offline)\n"
            "- 检查是否包含充分的单元测试\n"
            "- 公共方法是否有清晰的注释和文档\n"
            "- 注意边界条件与异常处理逻辑\n"
            "- 关注安全性：参数校验、日志脱敏、敏感信息处理\n"
            "- 建议你手动再看一遍关键业务逻辑\n"
        )
        return f"{offline}\n{AI_COMMENT_MARKER}"

    # 限制 diff 内容大小，避免 prompt 过长
    max_patch_chars = 6000
    diff_chunks: List[str] = []
    budget = max_patch_chars

    for ch in changes:
        patch = ch.get("patch") or ch.get("diff") or ""
        if not patch:
            continue
        snippet = patch[: min(budget, len(patch))]
        filename = ch.get("filename") or ch.get("new_path") or "unknown"
        diff_chunks.append(f"\n\n# File: {filename}\n{snippet}")
        budget -= len(snippet)
        if budget <= 0:
            break

    # 根据模式给出不同的提示语
    if mode == "report":
        mode_hint = (
            "Produce a structured, detailed review report with sections like "
            "Summary, Major issues, Minor issues, Tests, Security, Suggestions."
        )
    else:
        mode_hint = (
            "Produce concise, high-signal comments that can be posted as a single review comment. "
            "Prioritize critical issues."
        )

    system_prompt = (
        "You are a seasoned staff engineer performing code review. "
        "Focus on correctness, security, performance, readability, tests, and edge cases. "
        f"{mode_hint}"
    )

    user_prompt = (
        f"Repository: {repo}\n"
        f"Title: {title}\n"
        f"Description: {description or '(no description)'}\n"
        f"Please review the following changes and provide actionable feedback."
        f"{''.join(diff_chunks)}"
    )

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()

    return f"### 🤖 AI Review\n\n{content}\n\n{AI_COMMENT_MARKER}"


async def push_to_robot(push_url: str, text: str) -> None:
    """
    把简单文本推送到外部机器人，例如：
    - 企业微信机器人
    - 飞书机器人
    - Slack Incoming Webhook 等

    注意：不同平台的 payload 格式不一样，这里给一个企微/飞书常见的 text 模式示例，
    你可以根据实际情况调整分支。
    """
    if not push_url:
        return

    # 非关键逻辑，不要影响主流程
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # 企微 / 飞书 常见 text 消息格式
            payload = {
                "msgtype": "text",
                "text": {"content": text},
            }
            await client.post(push_url, json=payload)
    except Exception as e:
        # 简单打印日志即可，避免打断主流程
        print(f"push_to_robot error: {e}")


# ============================================================
# GitHub 相关：拉取 PR diff、创建/更新评论
# ============================================================

async def _github_fetch_pr_changes(owner: str, repo: str, number: int):
    """获取 GitHub PR 的改动文件和 PR 信息"""
    base = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        pr_resp = await client.get(f"{base}/pulls/{number}", headers=headers)
        pr_resp.raise_for_status()
        pr = pr_resp.json()

        files_resp = await client.get(f"{base}/pulls/{number}/files?per_page=100", headers=headers)
        files_resp.raise_for_status()
        files = files_resp.json()

    changes = [
        {
            "filename": f.get("filename"),
            "status": f.get("status"),
            "patch": f.get("patch", ""),
        }
        for f in files
    ]
    return changes, pr


async def _github_upsert_review_comment(owner: str, repo: str, number: int, body: str):
    """在 GitHub PR 下添加或更新 AI 评论"""
    base = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        comments_resp = await client.get(f"{base}/issues/{number}/comments?per_page=100", headers=headers)
        comments_resp.raise_for_status()
        comments = comments_resp.json()

        existing = next(
            (c for c in comments if AI_COMMENT_MARKER in (c.get("body") or "")), None)

        if existing:
            await client.patch(
                f"{base}/issues/comments/{existing['id']}",
                headers=headers,
                json={"body": body},
            )
        else:
            await client.post(
                f"{base}/issues/{number}/comments",
                headers=headers,
                json={"body": body},
            )


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: Optional[str] = Header(
        None, alias="X-Hub-Signature-256"),
    ai_mode: Optional[str] = Query(None, alias="ai_mode"),
):
    """
    GitHub Webhook 入口：
    - 验证签名
    - 只处理 pull_request 事件
    - 对 opened / synchronize / reopened / ready_for_review 执行 AI 评审
    """
    raw = await request.body()
    _verify_github_signature(x_hub_signature_256, raw)

    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if x_github_event != "pull_request":
        return JSONResponse({"ok": True, "skipped": f"event {x_github_event}"})

    action = payload.get("action")
    if action not in {"opened", "synchronize", "reopened", "ready_for_review"}:
        return JSONResponse({"ok": True, "skipped": f"action {action}"})

    pr = payload.get("pull_request", {})
    if pr.get("draft"):
        return JSONResponse({"ok": True, "skipped": "draft PR"})

    repo_full_name = payload["repository"]["full_name"]
    owner, repo = repo_full_name.split("/")
    number = pr["number"]

    changes, pr_obj = await _github_fetch_pr_changes(owner, repo, number)
    title = pr_obj.get("title", "")
    desc = pr_obj.get("body", "")

    # GitHub 这边可选通过 query 传 ai_mode（比如 /webhook/github?ai_mode=report）
    ai_mode_value = (ai_mode or "comment").lower()
    if ai_mode_value not in {"comment", "report"}:
        ai_mode_value = "comment"

    review = await _ai_review_summary(
        repo_full_name,
        title,
        desc,
        changes,
        mode=ai_mode_value,
    )

    await _github_upsert_review_comment(owner, repo, number, review)

    return {"ok": True, "reviewed": True}


# ============================================================
# GitLab 相关：拉取 MR diff、创建/更新评论
# ============================================================

async def _gitlab_fetch_mr_changes(
    project_id: int,
    iid: int,
    api_token: Optional[str] = None,
):
    """
    获取 GitLab MR 改动文件和 MR 信息。

    api_token:
      - 优先使用来自 Webhook 自定义头 X-Gitlab-Api-Token
      - 若为空，则回退到环境变量 GITLAB_TOKEN
    """
    token = api_token or GITLAB_TOKEN
    headers = {"PRIVATE-TOKEN": token} if token else {}

    async with httpx.AsyncClient(timeout=30) as client:
        mr_resp = await client.get(
            f"{GITLAB_API_BASE}/projects/{project_id}/merge_requests/{iid}",
            headers=headers,
        )
        mr_resp.raise_for_status()
        mr = mr_resp.json()

        changes_resp = await client.get(
            f"{GITLAB_API_BASE}/projects/{project_id}/merge_requests/{iid}/changes",
            headers=headers,
        )
        changes_resp.raise_for_status()
        changes = changes_resp.json().get("changes", [])

    normalized: List[Dict[str, Any]] = []
    for f in changes:
        status = "modified"
        if f.get("new_file"):
            status = "added"
        elif f.get("deleted_file"):
            status = "removed"
        elif f.get("renamed_file"):
            status = "renamed"

        normalized.append(
            {
                "filename": f.get("new_path") or f.get("old_path"),
                "status": status,
                "patch": f.get("diff", ""),
            }
        )

    return normalized, mr


async def _gitlab_upsert_note(
    project_id: int,
    iid: int,
    body: str,
    api_token: Optional[str] = None,
):
    """在 GitLab MR 下添加或更新 AI 评论"""
    token = api_token or GITLAB_TOKEN
    headers = {"PRIVATE-TOKEN": token} if token else {}

    async with httpx.AsyncClient(timeout=30) as client:
        notes_resp = await client.get(
            f"{GITLAB_API_BASE}/projects/{project_id}/merge_requests/{iid}/notes?per_page=100",
            headers=headers,
        )
        notes_resp.raise_for_status()
        notes = notes_resp.json()

        existing = next(
            (n for n in notes if AI_COMMENT_MARKER in (n.get("body") or "")), None)

        if existing:
            await client.put(
                f"{GITLAB_API_BASE}/projects/{project_id}/merge_requests/{iid}/notes/{existing['id']}",
                headers=headers,
                json={"body": body},
            )
        else:
            await client.post(
                f"{GITLAB_API_BASE}/projects/{project_id}/merge_requests/{iid}/notes",
                headers=headers,
                json={"body": body},
            )


@app.post("/webhook/gitlab")
async def gitlab_webhook(
    request: Request,
    # GitLab 用于 webhook 验证的 Secret token，会出现在 X-Gitlab-Token 里
    x_gitlab_token: Optional[str] = Header(None, alias="X-Gitlab-Token"),
    # 自定义：控制 AI 输出风格
    x_ai_mode: Optional[str] = Header(None, alias="X-Ai-Mode"),
    # 自定义：外部机器人地址（企微、飞书等）
    x_push_url: Optional[str] = Header(None, alias="X-Push-Url"),
    # 自定义：GitLab API Access Token，可覆盖环境变量中的 GITLAB_TOKEN
    x_gitlab_api_token: Optional[str] = Header(
        None, alias="X-Gitlab-Api-Token"),
):
    """
    GitLab Webhook 入口：

    - 使用 X-Gitlab-Token 验证 webhook 来源
    - 使用 X-Ai-Mode 控制 AI 输出风格：report / comment
    - 使用 X-Push-Url 将状态推送到企微 / 飞书等机器人
    - 使用 X-Gitlab-Api-Token 调用 GitLab API（可选）
    """
    raw = await request.body()
    _verify_gitlab_token(x_gitlab_token)

    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if payload.get("object_kind") != "merge_request":
        return JSONResponse({"ok": True, "skipped": f"kind {payload.get('object_kind')}"})

    attrs = payload.get("object_attributes", {})
    action = attrs.get("action")
    state = attrs.get("state")
    title = attrs.get("title", "") or ""

    if action not in {"open", "reopen", "update"} or state not in {"opened", "open"}:
        return JSONResponse({"ok": True, "skipped": f"action/state {action}/{state}"})

    if attrs.get("work_in_progress") or title.lower().startswith(("wip", "draft")):
        return JSONResponse({"ok": True, "skipped": "draft/WIP"})

    project = payload.get("project", {})
    project_id = project.get("id")
    iid = attrs.get("iid")

    if not (project_id and iid):
        raise HTTPException(
            status_code=400, detail="Missing project_id or iid")

    # 处理 AI 模式
    ai_mode_value = (x_ai_mode or "comment").lower()
    if ai_mode_value not in {"comment", "report"}:
        ai_mode_value = "comment"

    push_url = x_push_url or ""
    api_token = x_gitlab_api_token or None

    # 拉取 MR diff 并调用 AI 生成评审
    changes, mr_obj = await _gitlab_fetch_mr_changes(project_id, iid, api_token=api_token)
    desc = mr_obj.get("description", "") or ""
    repo_label = f"gitlab:{project.get('path_with_namespace', project_id)}"

    review = await _ai_review_summary(
        repo_label,
        title,
        desc,
        changes,
        mode=ai_mode_value,
    )

    # 写回 MR 评论
    await _gitlab_upsert_note(project_id, iid, review, api_token=api_token)

    # 推送状态到外部机器人（可选）
    if push_url:
        summary = f"[GitLab] {repo_label} MR !{iid}: {title}\nAI 模式: {ai_mode_value}\nAI 评论已生成。"
        await push_to_robot(push_url, summary)

    return {"ok": True, "reviewed": True}


# ============================================================
# 健康检查与本地启动
# ============================================================

@app.get("/healthz")
async def healthz():
    """健康检查，用于存活探针"""
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
