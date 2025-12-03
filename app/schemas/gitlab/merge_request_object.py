from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class MRObjUser(BaseModel):
    id: int
    username: str
    public_email: Optional[str] = None
    name: str
    state: str
    locked: bool
    avatar_url: Optional[str] = None
    web_url: Optional[str] = None


class MRObjReferences(BaseModel):
    short: str
    relative: str
    full: str


class MRObjTimeStats(BaseModel):
    time_estimate: int
    total_time_spent: int
    human_time_estimate: Optional[Any] = None
    human_total_time_spent: Optional[Any] = None


class MRObjTaskCompletionStatus(BaseModel):
    count: int
    completed_count: int


class MRObjDiffRefs(BaseModel):
    base_sha: str
    head_sha: str
    start_sha: str


class MRObj(BaseModel):
    id: int
    iid: int
    project_id: int
    title: str
    description: str
    state: str
    created_at: str
    updated_at: str
    merged_by: Optional[Any] = None
    merge_user: Optional[Any] = None
    merged_at: Optional[Any] = None
    closed_by: Optional[Any] = None
    closed_at: Optional[Any] = None
    target_branch: str
    source_branch: str
    user_notes_count: int
    upvotes: int
    downvotes: int

    author: MRObjUser
    assignees: List[Any]
    assignee: Optional[Any] = None
    reviewers: List[Any]

    source_project_id: int
    target_project_id: int

    labels: List[Any]

    draft: bool
    imported: bool
    imported_from: Optional[str] = None
    work_in_progress: bool

    milestone: Optional[Any] = None

    merge_when_pipeline_succeeds: bool
    merge_status: str
    detailed_merge_status: str

    merge_after: Optional[Any] = None
    sha: str
    merge_commit_sha: Optional[Any] = None
    squash_commit_sha: Optional[Any] = None

    discussion_locked: Optional[bool] = None
    should_remove_source_branch: Optional[Any] = None
    force_remove_source_branch: Optional[bool] = None

    prepared_at: str
    reference: str
    references: MRObjReferences
    web_url: str

    time_stats: MRObjTimeStats
    squash: bool
    squash_on_merge: bool

    task_completion_status: MRObjTaskCompletionStatus
    has_conflicts: bool
    blocking_discussions_resolved: bool
    approvals_before_merge: Optional[Any] = None

    subscribed: bool
    changes_count: str

    latest_build_started_at: Optional[Any] = None
    latest_build_finished_at: Optional[Any] = None
    first_deployed_to_production_at: Optional[Any] = None

    pipeline: Optional[Any] = None
    head_pipeline: Optional[Any] = None

    diff_refs: MRObjDiffRefs

    merge_error: Optional[Any] = None
    first_contribution: bool

    user: Dict[str, Any]
