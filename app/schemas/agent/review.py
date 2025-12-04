from typing import Optional, List, Literal, Any
from pydantic import BaseModel, Field


class Message(BaseModel):
    """Message type"""
    content: str
    role: str


class Delta(BaseModel):
    """Delta type"""
    content: str


class Choice(BaseModel):
    """Choice type"""
    finish_reason: Optional[str] = None
    index: int
    message: Optional[Message] = None
    delta: Optional[Delta] = None
    logprobs: Any = None


class PromptTokensDetails(BaseModel):
    """Prompt tokens details"""
    cached_tokens: int


class Usage(BaseModel):
    """Usage information"""
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int
    prompt_tokens_details: Optional[PromptTokensDetails] = None
    prompt_cache_hit_tokens: Optional[int] = None
    prompt_cache_miss_tokens: Optional[int] = None


class QWenChatResponse(BaseModel):
    """QWen chat response"""
    id: str
    choices: List[Choice]
    created: int
    model: str
    object: str
    system_fingerprint: Optional[str] = None
    usage: Optional[Usage] = None


class Review(BaseModel):
    """Code review"""
    # Represents the file path after modification
    new_path: str = Field(..., alias='newPath')
    # Represents the file path before modification
    old_path: str = Field(..., alias='oldPath')
    # Indicates whether reviewing old or new code, if reviewing + part of code, type is new
    # if reviewing - part of code, type is old.
    type: Literal['old', 'new']
    # If old type, start_line represents the start_line of old code
    # otherwise represents the start_line of new code
    start_line: int = Field(..., alias='startLine')
    # If new type, end_line represents the end_line of old code
    # otherwise represents the end_line of new code
    end_line: int = Field(..., alias='endLine')
    # Title summarizing the issue (e.g., logic error, syntax error, security risk, etc.)
    # preferably no more than 6 words
    issue_header: str = Field(..., alias='issueHeader')
    # Clearly describe the issue that exists, needs attention
    # or should be modified in the code, and provide clear suggestions
    issue_content: str = Field(..., alias='issueContent')

    class Config:
        populate_by_name = True  # Allow using both alias and field name


class MRReview(BaseModel):
    """MR review"""
    reviews: List[Review]


class YamlContent(BaseModel):
    """YAML content"""
    content: str
    parsed: Optional[MRReview] = None
    error: Any = None
    fix_applied: Optional[bool] = Field(None, alias='fixApplied')
    fixed_content: Optional[str] = Field(None, alias='fixedContent')

    class Config:
        populate_by_name = True  # Allow using both alias and field name
        # Allow arbitrary types (for error field)
        arbitrary_types_allowed = True
