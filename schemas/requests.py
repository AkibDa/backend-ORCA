from uuid import UUID

from pydantic import BaseModel, Field


class OrcaQueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural-language marine query",
    )
    session_id: UUID | None = Field(
        None,
        description="Optional conversation session identifier",
    )
    location: str | None = Field(
        None,
        description="Optional location context from the frontend",
    )
