from typing import Optional
from pydantic import BaseModel


class GithubDiffItem(BaseModel):
    """GitHub file diff item"""
    diff: str  # The patch content
    new_path: str  # filename
    old_path: str  # previous_filename or filename
    new_file: bool = False  # status == 'added'
    renamed_file: bool = False  # status == 'renamed'
    deleted_file: bool = False  # status == 'removed'
    
    # Optional fields for compatibility
    collapsed: bool = False
    too_large: bool = False
    a_mode: Optional[str] = None
    b_mode: Optional[str] = None
    generated_file: bool = False