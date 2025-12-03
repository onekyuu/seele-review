from __future__ import annotations

from os import wait
from typing import Any, Dict, Iterable, List, Optional

import httpx
from fastapi import HTTPException

from app.config import settings


class GitlabApiError(Exception):
    pass


class GitlabClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _verify_gitlab_signature(self, token: Optional[str]):
        if not settings.gitlab_webhook_secret:
            raise HTTPException(
                status_code=400, detail="Missing GITLAB_WEBHOOK_SECRET configuration"
            )
        if token is None:
            raise HTTPException(status_code=400, detail="Missing X-Gitlab-Token header")
        if token != settings.gitlab_webhook_secret:
            raise HTTPException(status_code=401, detail="Invalid GitLab token")

    async def _get_gitlab_mr_diff(
        self, project_id: int, iid: int, api_token: Optional[str] = None
    ):
        """Get GitLab merge request diff"""
        token = api_token or settings.gitlab_token
        headers = {"PRIVATE-TOKEN": token} if token else {}
        async with httpx.AsyncClient(timeout=30) as client:
            mr_resp = await client.get(
                f"{settings.gitlab_api_base}/projects/{project_id}/merge_requests/{iid}",
                headers=headers,
            )
            mr_resp.raise_for_status()
            mr_obj = mr_resp.json()

            diff_resp = await client.get(
                f"{settings.gitlab_api_base}/projects/{project_id}/merge_requests/{iid}/changes",
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


# ALLOWED_CODE_EXTS = {
#     ".ts",
#     ".tsx",
#     ".js",
#     ".jsx",
#     ".vue",
#     ".mjs",
#     ".cjs",
#     ".json",
#     ".py",
#     ".java",
#     ".go",
#     ".rs",
#     ".php",
#     ".rb",
#     ".cs",
#     ".kt",
#     ".kts",
#     ".scala",
#     ".c",
#     ".h",
#     ".cpp",
#     ".hpp",
#     ".mdx",
# }
#
#
# BLOCKED_SUFFIXES = {
#     ".min.js",
#     ".lock",
#     ".map",
# }
#
#
# def _is_code_file(path: str) -> bool:
#     lower = path.lower()
#
#     for suf in BLOCKED_SUFFIXES:
#         if lower.endswith(suf):
#             return False
#
#     for ext in ALLOWED_CODE_EXTS:
#         if lower.endswith(ext):
#             return True
#
#     return False
#
#
# def filter_changes_for_ai(changes: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
#     result: list[dict[str, Any]] = []
#
#     for change in changes:
#         new_path = change.get("new_path") or ""
#         old_path = change.get("old_path") or ""
#
#         path_for_check = new_path or old_path
#         if not path_for_check:
#             continue
#
#         if _is_code_file(path_for_check):
#             result.append(change)
#
#     return result
