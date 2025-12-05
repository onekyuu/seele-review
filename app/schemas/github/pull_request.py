from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class User(BaseModel):
    """GitHub User"""
    login: str
    id: int
    node_id: str
    avatar_url: Optional[str] = None
    gravatar_id: Optional[str] = None
    url: Optional[str] = None
    html_url: Optional[str] = None
    type: Optional[str] = None
    site_admin: Optional[bool] = None


class Repository(BaseModel):
    """GitHub Repository"""
    id: int
    node_id: str
    name: str
    full_name: str
    private: bool
    owner: User
    html_url: str
    description: Optional[str] = None
    fork: bool
    url: str
    default_branch: str
    language: Optional[str] = None
    visibility: Optional[str] = None


class BranchInfo(BaseModel):
    """GitHub Branch Information"""
    label: str
    ref: str
    sha: str
    user: User
    repo: Repository


class PullRequest(BaseModel):
    """GitHub Pull Request"""
    url: str
    id: int
    node_id: str
    html_url: str
    diff_url: str
    patch_url: str
    issue_url: str
    number: int
    state: str
    locked: bool
    title: str
    user: User
    body: Optional[str] = None
    created_at: str
    updated_at: str
    closed_at: Optional[str] = None
    merged_at: Optional[str] = None
    merge_commit_sha: Optional[str] = None
    assignee: Optional[User] = None
    assignees: List[User] = []
    requested_reviewers: List[User] = []
    requested_teams: List[Dict[str, Any]] = []
    labels: List[Dict[str, Any]] = []
    milestone: Optional[Dict[str, Any]] = None
    draft: bool
    commits_url: str
    review_comments_url: str
    review_comment_url: str
    comments_url: str
    statuses_url: str
    head: BranchInfo
    base: BranchInfo
    author_association: str
    auto_merge: Optional[Dict[str, Any]] = None
    active_lock_reason: Optional[str] = None
    merged: bool
    mergeable: Optional[bool] = None
    rebaseable: Optional[bool] = None
    mergeable_state: str
    merged_by: Optional[User] = None
    comments: int
    review_comments: int
    maintainer_can_modify: bool
    commits: int
    additions: int
    deletions: int
    changed_files: int

    # _links field
    links: Optional[Dict[str, Any]] = Field(None, alias="_links")


class GithubPullRequestPayload(BaseModel):
    """GitHub Pull Request Webhook Payload"""
    action: str
    number: int
    pull_request: PullRequest
    repository: Repository
    sender: User

    class Config:
        populate_by_name = True  # Allow field aliases
