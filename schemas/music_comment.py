from typing import Optional
from pydantic import BaseModel, constr


class MusicCommentCreate(BaseModel):
    content: constr(strip_whitespace=True, min_length=1, max_length=1000)
    parent_id: Optional[int] = None
