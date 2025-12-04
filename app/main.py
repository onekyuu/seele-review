from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas.gitlab.merge_request import GitlabMergeRequestPayload
from app.services.gitlab import GitlabApiError, GitlabClient
from app.services.patch.gitlab import PatchHandler
from app.services.agent.agent import AgentService
from app.services.prompt.prompt import PromptService

app = FastAPI(title="SEELE Review FastAPI", version="0.1.0")

gitlab_client = GitlabClient(settings.gitlab_api_base)

prompt_service = PromptService()
agent_service = AgentService(prompt_service)


@app.post("/webhook/gitlab")
async def handle_gitlab_webhook_trigger(
    request: Request,
    x_ai_mode: Optional[str] = Header(None, alias="X-Ai-Mode"),
    x_push_url: Optional[str] = Header(None, alias="X-Push-Url"),
    x_gitlab_token: Optional[str] = Header(None, alias="X-Gitlab-Token"),
):
    """gitlab webhook endpoint"""
    gitlab_client._verify_gitlab_signature(x_gitlab_token)
    raw = await request.body()

    try:
        payload = GitlabMergeRequestPayload.model_validate_json(raw)
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail="Invalid JSON payload") from exc

    if payload.object_kind != "merge_request":
        return JSONResponse({"ok": True, "skipped": f"kind {payload.object_kind}"})

    attrs = payload.object_attributes or {}
    action = attrs.action
    state = attrs.state
    title = attrs.title or ""

    if action not in {"open", "reopen", "update"} or state not in {"opened", "open"}:
        return JSONResponse({"ok": True, "skipped": f"action/state {action}/{state}"})

    if attrs.work_in_progress or title.lower().startswith(("wip", "draft")):
        return JSONResponse({"ok": True, "skipped": "draft/WIP"})

    project_id = payload.project.id
    iid = attrs.iid

    if not (project_id and iid):
        raise HTTPException(
            status_code=400, detail="Missing project_id or iid")

    ai_mode = (x_ai_mode or "comment").lower()
    if ai_mode not in ("comment", "report"):
        ai_mode = "comment"

    push_url = x_push_url or ""
    api_token = settings.gitlab_token or None

    try:
        diff, mr_obj = await gitlab_client._get_gitlab_mr_diff(
            project_id, iid, api_token=api_token
        )
    except GitlabApiError as e:
        print(f"[ERROR] get gitlab mr diff failed: {e}")
        return JSONResponse(
            {"message": "failed to fetch changes from gitlab",
                "error": str(e)},
            status_code=500,
        )
    desc = mr_obj.description or ""
    repo_label = f"gitlab:{payload.project.path_with_namespace}"
    patch_handler = PatchHandler(diff)
    extended_diff = patch_handler.get_extended_diff_content(
        commit_message=attrs.title or "")

    # 调用 AgentService 获取代码审查结果
    try:
        reviews = await agent_service.get_prediction(extended_diff)
    except Exception as e:
        print(f"[ERROR] AI prediction failed: {e}")
        return JSONResponse(
            {"message": "AI review failed", "error": str(e)},
            status_code=500,
        )

    print(
        f"Processing GitLab MR !{iid} in project {project_id} with AI mode {ai_mode}")
    print(f"MR Diff:\n{diff}")
    print(f"MR Extended Diff: \n{extended_diff}")
    print(f"AI Reviews: {reviews}")

    # return JSONResponse({"ok": True, "reviews": reviews})
