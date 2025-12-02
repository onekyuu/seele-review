from typing import Any, Optional

from pydantic import BaseModel, Field


class GitlabProject(BaseModel):
    id: int
    name: str
    path_with_namespace: str | None = None
    web_url: str | None = None


class GitlabUser(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None


class GitlabObjectAttributes(BaseModel):
    id: int
    iid: int
    target_branch: str
    source_branch: str
    title: str
    description: Optional[str] = None
    state: Optional[str] = None
    url: Optional[str] = Field(default=None, alias="url")
    last_commit: Optional[dict[str, Any]] = None


class GitlabMergeRequestEvent(BaseModel):
    object_kind: str
    event_type: Optional[str] = None
    project: GitlabProject
    user: Optional[GitlabUser] = None
    object_attributes: GitlabObjectAttributes

    class Config:
        populate_by_name = True
