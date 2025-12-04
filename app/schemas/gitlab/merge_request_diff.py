from typing import Dict, List, Optional

from pydantic import BaseModel


class MRDiffItem(BaseModel):
    diff: str
    collapsed: bool
    too_large: bool
    new_path: str
    old_path: str
    a_mode: str
    b_mode: str
    new_file: bool
    renamed_file: bool
    deleted_file: bool
    generated_file: bool
    extended_diff: Optional[str] = None
    new_lines_with_number: Optional[Dict[int, str]] = None
    old_lines_with_number: Optional[Dict[int, str]] = None


class DiffRefs(BaseModel):
    base_sha: str
    head_sha: str
    start_sha: str


class MRDiff(BaseModel):
    changes: List[MRDiffItem]
    diff_refs: DiffRefs
