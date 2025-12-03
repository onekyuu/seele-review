from typing import Any, Dict, List, Optional

from pydantic import BaseModel

# ---- Sub models ----


class GitlabUser(BaseModel):
    id: int
    name: str
    username: str
    avatar_url: Optional[str] = None
    email: Optional[str] = None


class GitlabProject(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    web_url: str
    avatar_url: Optional[str] = None
    git_ssh_url: Optional[str] = None
    git_http_url: Optional[str] = None
    namespace: Optional[str] = None
    visibility_level: Optional[int] = None
    path_with_namespace: Optional[str] = None
    default_branch: Optional[str] = None
    ci_config_path: Optional[str] = None
    homepage: Optional[str] = None
    url: Optional[str] = None
    ssh_url: Optional[str] = None
    http_url: Optional[str] = None


class GitlabMergeParams(BaseModel):
    force_remove_source_branch: Optional[str] = None


class GitlabCommitAuthor(BaseModel):
    name: str
    email: str


class GitlabLastCommit(BaseModel):
    id: str
    message: str
    title: str
    timestamp: str
    url: str
    author: GitlabCommitAuthor


class GitlabObjectAttributes(BaseModel):
    assignee_id: Optional[int] = None
    author_id: int
    created_at: str
    description: str
    draft: bool
    head_pipeline_id: Optional[int] = None
    id: int
    iid: int
    title: str
    merge_status: str
    merge_user_id: Optional[int] = None
    merge_when_pipeline_succeeds: bool
    milestone_id: Optional[int] = None
    source_branch: str
    source_project_id: int
    state_id: int
    target_branch: str
    target_project_id: int
    time_estimate: int
    updated_at: str
    prepared_at: Optional[str] = None
    assignee_ids: List[Any]
    blocking_discussions_resolved: bool
    detailed_merge_status: str
    first_contribution: bool
    labels: List[Any]
    last_commit: GitlabLastCommit
    reviewer_ids: List[Any]
    source: GitlabProject
    state: str
    system: bool
    target: GitlabProject
    time_change: int
    total_time_spent: int
    url: str
    work_in_progress: bool
    approval_rules: List[Any]
    action: str
    merge_params: GitlabMergeParams
    last_edited_at: Optional[str] = None
    last_edited_by_id: Optional[int] = None
    human_time_change: Optional[Any] = None
    human_time_estimate: Optional[Any] = None
    human_total_time_spent: Optional[Any] = None


class GitlabChangesItem(BaseModel):
    previous: Optional[Any] = None
    current: Optional[Any] = None


class GitlabChanges(BaseModel):
    merge_status: Optional[GitlabChangesItem] = None
    updated_at: Optional[GitlabChangesItem] = None
    prepared_at: Optional[GitlabChangesItem] = None


class GitlabRepository(BaseModel):
    name: str
    url: str
    description: Optional[str] = None
    homepage: str


# ---- Main Webhook Model ----


class GitlabMergeRequestPayload(BaseModel):
    object_kind: str
    event_type: Optional[str] = None
    user: GitlabUser
    project: GitlabProject
    object_attributes: GitlabObjectAttributes
    labels: List[Any]
    changes: GitlabChanges
    repository: GitlabRepository
