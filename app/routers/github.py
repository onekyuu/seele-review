from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import settings
from app.schemas.github.pull_request import GithubPullRequestPayload
from app.services.github import GithubApiError, GithubClient
from app.services.patch.github import GithubPatchHandler
from app.services.agent.agent import AgentService
from app.services.prompt.prompt import PromptService
from app.services.publish.github import GithubPublishService

router = APIRouter(prefix="/webhook", tags=["github"])

# Initialize services
github_client = GithubClient(settings.github_api_base)
prompt_service = PromptService()
agent_service = AgentService(prompt_service)
publish_service = GithubPublishService(
    github_api_base=settings.github_api_base,
    github_token=settings.github_token,
    bot_name="🤖 AI Review Bot"
)


@router.post("/github")
async def handle_github_webhook_trigger(
    request: Request,
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    x_hub_signature: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    ai_mode: Optional[str] = Query(None, alias="mode"),
    push_url: Optional[str] = Query(None, alias="push_url"),
    token: Optional[str] = Query(None, alias="token"),
):
    """
    GitHub webhook endpoint

    Webhook URL format:
    https://your-domain.com/webhook/github?mode=comment&push_url=https://...

    Query Parameters:
    - mode: Review mode (comment/report), default: comment
    - push_url: Notification webhook URL (e.g., Slack, WeCom, Feishu bot)
    - token: (Optional) GitHub access token. Use GITHUB_TOKEN env var instead.
    """
    raw = await request.body()

    # Verify GitHub signature
    try:
        github_client._verify_github_signature(x_hub_signature, raw)
    except Exception as e:
        raise HTTPException(
            status_code=401, detail=f"Invalid signature: {str(e)}")

    # Only process pull_request events
    if x_github_event != "pull_request":
        return JSONResponse({
            "ok": True,
            "skipped": f"event {x_github_event}"
        })

    # Parse payload
    try:
        payload = GithubPullRequestPayload.model_validate_json(raw)
    except ValidationError as exc:
        for error in exc.errors():
            print(f"  Field: {error['loc']}, Error: {error['msg']}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid pull_request payload: {exc.errors()}"
        ) from exc

    action = payload.action
    pr = payload.pull_request

    if not pr:
        raise HTTPException(
            status_code=400, detail="Missing pull_request data")

    # Only process opened, reopened, synchronize actions
    if action not in {"opened", "reopened", "synchronize"}:
        return JSONResponse({"ok": True, "skipped": f"action {action}"})

    # Skip draft PRs
    if pr.draft:
        return JSONResponse({"ok": True, "skipped": "draft PR"})

    owner = payload.repository.owner.login
    repo = payload.repository.name
    pr_number = pr.number

    # Process query parameters
    review_mode = (ai_mode or "comment").lower()
    if review_mode not in ("comment", "report"):
        review_mode = "comment"

    notification_url = push_url or settings.notification_webhook_url or ""

    # Use token from environment variable
    api_token = settings.github_token or token
    if not api_token:
        raise HTTPException(
            status_code=400,
            detail="GitHub token not configured. Set GITHUB_TOKEN in .env file"
        )

    if token:
        print("[WARNING] Token passed in URL. Use environment variable instead!")

    # Fetch PR diff
    try:
        diff_items, pr_obj = await github_client._get_github_pr_diff(
            owner, repo, pr_number, api_token=api_token
        )
    except GithubApiError as e:
        return JSONResponse(
            {"message": "failed to fetch changes from github",
                "error": str(e)},
            status_code=500,
        )

    if not diff_items:
        return JSONResponse({
            "ok": True,
            "message": "No file changes to review"
        })

    # Use GitHub-specific PatchHandler
    patch_handler = GithubPatchHandler(diff_items)

    # Check if there are code changes
    if not patch_handler.has_code_changes():
        return JSONResponse({
            "ok": True,
            "message": "No code file changes to review"
        })

    # Get extended diff for AI analysis
    extended_diff = patch_handler.get_extended_diff_content(
        commit_message=pr.title or ""
    )

    # Call AgentService to get code review results
    try:
        reviews = await agent_service.get_prediction(extended_diff)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"message": "AI review failed", "error": str(e)},
            status_code=500,
        )

    # Publish review results
    if reviews:
        try:
            callback = {
                'push_url': notification_url,
                'user_name': payload.sender.login if payload.sender else 'Unknown',
                'project_name': payload.repository.full_name,
                'pr_title': pr.title,
                'pr_url': pr.html_url,
            }

            await publish_service.publish(
                mode=review_mode,
                reviews=reviews,
                pr_obj=pr_obj,
                diff_items=diff_items,
                owner=owner,
                repo=repo,
                pr_number=pr_number,
                callback=callback
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JSONResponse(
                {"message": "Failed to publish reviews", "error": str(e)},
                status_code=500,
            )
    else:
        print("[INFO] No issues found by AI review")

    return JSONResponse({
        "ok": True,
        "reviews_count": len(reviews) if reviews else 0,
        "mode": review_mode,
        "pr_number": pr_number
    })
