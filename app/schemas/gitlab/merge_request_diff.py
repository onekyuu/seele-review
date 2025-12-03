from typing import Any, Dict, List, Optional

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


class MRDiff(BaseModel):
    changes: List[MRDiffItem]
