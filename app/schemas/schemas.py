from typing import Optional

from pydantic import BaseModel, Field


class ResponseItem(BaseModel):
    content: str = Field(min_length=1)
    description: Optional[str] = None
    request_id: Optional[str] = None
