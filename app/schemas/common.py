from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str


class PaginatedMeta(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int


class TimestampSchema(BaseModel):
    created_at: datetime
    updated_at: datetime
