from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas.gitlab import GitlabMergeRequestEvent

app = FastAPI(title="SEELE Review FastAPI", version="0.1.0")


@app.post("/webhook/gitlab")
async def handle_webhook_trigger(
    request: Request,
    event: GitlabMergeRequestEvent,
    x_ai_mode: str | None = Header(default=None, alias="x-ai-mode"),
    x_push_url: str | None = Header(default=None, alias="x-push-url"),
    x_gitlab_token: str | None = Header(default=None, alias="x-gitlab-token"),
    x_gitlab_event: str | None = Header(default=None, alias="x-gitlab-event"),
):
    print("=== Request ===", request)
    if x_gitlab_event not in ("Merge Request Hook", "Merge Request Event"):
        return JSONResponse(
            {"message": "ignored event", "x_gitlab_event": x_gitlab_event},
            status_code=200,
        )

    mr = event.object_attributes
    project = event.project

    ai_mode = x_ai_mode or settings.defalut_ai_mode
    push_url = x_push_url or settings.slack_webhook_ai_review
    gitlab_token = x_gitlab_token

    if settings.debug:
        print("=== MR Webhook Received ===")
        print(
            f"project: {project.path_with_namespace or project.name} (id={project.id})"
        )
        print(
            f"mr: !{mr.iid} [{mr.source_branch} -> {mr.target_branch}] title={mr.title}"
        )
        print(f"ai_mode: {ai_mode}")
        print(f"push_url: {push_url}")
        print(f"x_gitlab_token: {bool(gitlab_token)}")
        print("============================")

    return {
        "message": "webhook received",
        "project_id": project.id,
        "mr_iid": mr.iid,
        "ai_mode": ai_mode,
    }
