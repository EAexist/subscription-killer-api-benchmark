from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class GmailMessage(BaseModel):
    """Gmail message data structure matching the Kotlin data class."""

    model_config = ConfigDict(populate_by_name=True)
    id: str
    internalDate: int  # Unix timestamp in milliseconds
    senderName: Optional[str]
    senderEmail: str
    subject: str
    snippet: str
    templateId: Optional[str] = None


class BatchGetRequest(BaseModel):
    """Request model for batch getting messages."""

    message_ids: List[str]


class FirstMessageIdRequest(BaseModel):
    """Request model for getting first message ID by addresses."""

    addresses: List[str]


class BatchGetResponse(BaseModel):
    """Response model for batch getting messages."""

    messages: List[GmailMessage]


class FirstMessageRequest(BaseModel):
    """Request model for getting first message by addresses."""

    addresses: List[str]


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    messages_per_request: int
