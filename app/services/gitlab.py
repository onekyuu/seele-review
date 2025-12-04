from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import httpx
from fastapi import HTTPException

from app.config import settings
from app.schemas.gitlab.merge_request_diff import MRDiff, MRDiffItem
from app.schemas.gitlab.merge_request_object import MRObj

CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".html",
    ".css",
    ".scss",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".yml",
    ".yaml",
    ".toml",
    ".sh",
    ".sql",
}


class GitlabApiError(Exception):
    pass


class GitlabClient:
    def __init__(self, base_url: str, code_extensions: Optional[set[str]] = None):
        self.base_url = base_url.rstrip("/")
        self.code_extensions = code_extensions or CODE_EXTENSIONS

    def _verify_gitlab_signature(self, token: Optional[str]):
        if not settings.gitlab_webhook_secret:
            raise HTTPException(
                status_code=400, detail="Missing GITLAB_WEBHOOK_SECRET configuration"
            )
        if token is None:
            raise HTTPException(
                status_code=400, detail="Missing X-Gitlab-Token header")
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
            mr_obj = MRObj.model_validate(mr_resp.json())

            diff_response = await client.get(
                f"{settings.gitlab_api_base}/projects/{project_id}/merge_requests/{iid}/changes",
                headers=headers,
            )
            diff_response.raise_for_status()
            changes = MRDiff.model_validate(diff_response.json()).changes or []
            diff_refs = MRDiff.model_validate(diff_response.json()).diff_refs
            filtered_changes = self.filter_no_code_file(changes)

        return filtered_changes, mr_obj

    def filter_no_code_file(self, diffs: List[MRDiffItem]) -> List[MRDiffItem]:
        filtered = []

        for item in diffs:
            filename = item.new_path or item.old_path
            ext = self._get_extension(filename)

            if ext in self.code_extensions:
                filtered.append(item)

        return filtered

    def _get_extension(self, filename: str) -> str:
        if "." not in filename:
            return ""
        return "." + filename.split(".")[-1]
