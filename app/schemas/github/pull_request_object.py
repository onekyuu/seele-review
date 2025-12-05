from typing import Optional, Dict, Any
from pydantic import BaseModel


class PRObj(BaseModel):
    """GitHub Pull Request object"""
    id: int
    number: int
    title: str
    body: Optional[str] = None
    state: str
    html_url: str
    diff_url: str
    user: Dict[str, Any]
    created_at: str
    updated_at: str
    head: Dict[str, Any]
    base: Dict[str, Any]