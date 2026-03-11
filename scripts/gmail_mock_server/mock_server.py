import logging
from typing import Optional

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError

# Configure logging to show debug messages
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Import models, services, and configuration
from config import settings
from models import (
    BatchGetRequest,
    BatchGetResponse,
    FirstMessageIdRequest,
    GmailMessage,
    HealthResponse,
)
from state import app_state
from utils.data_utils import MessageUtils

app = FastAPI()


# Add exception handler to catch validation errors and log request details
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logging.debug(f"Validation error for {request.method} {request.url}")
    logging.debug(f"Request headers: {dict(request.headers)}")

    # Try to get the body that caused the validation error
    try:
        # This will work because the body hasn't been consumed yet
        body = await request.body()
        if body:
            logging.debug(
                f"Request body that failed validation: {body.decode('utf-8')}"
            )
    except Exception as e:
        logging.debug(f"Could not read request body: {e}")

    logging.debug(f"Validation error details: {exc.errors()}")

    # Return the default 422 response
    raise HTTPException(status_code=422, detail=exc.errors())


# Initialize data on startup
app_state.initialize()


@app.get("/health")
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy", total_messages=len(app_state.gmail_messages)
    )


@app.get("/messages")
async def list_message_ids(
    q: Optional[str] = None,  # Legacy parameter - ignored for compatibility
    x_mock_user: Optional[str] = Header(None),
):
    """
    Gmail API endpoint for listing message IDs with configurable distribution.

    Args:
        q: Legacy query parameter (ignored - maintained for API compatibility only)
        x_mock_user: Mock user header

    Returns:
        Comma-separated list of message IDs
    """
    # Use distribution-based selection with configured settings
    selected_messages = app_state.message_selector.select_messages(
        count=settings.n_emails_per_request
    )

    # Extract message IDs
    message_ids = MessageUtils.extract_message_ids(selected_messages)

    # Return as plain text list to match simple parsing in client
    return ",".join(message_ids)


@app.post("/messages/batch-get")
async def get_messages(request: BatchGetRequest) -> BatchGetResponse:
    """
    Gmail API endpoint for batch getting messages.
    Returns full message details for the provided IDs.
    """
    message_ids = request.message_ids

    messages = []
    for msg_id in message_ids:
        if msg_id in app_state.message_map:
            msg = app_state.message_map[msg_id]
            messages.append(
                GmailMessage(
                    id=msg.id,
                    internalDate=msg.internalDate,
                    senderName=msg.senderName,
                    senderEmail=msg.senderEmail,
                    subject=msg.subject,
                    snippet=msg.snippet,
                )
            )

    return BatchGetResponse(messages=messages)


@app.post("/messages/first")
async def get_first_message_id(request: FirstMessageIdRequest):
    """
    Gmail API endpoint for getting first message ID by addresses.
    Returns the first message ID found from the given addresses.
    """
    # Find first message from any of the provided addresses
    for msg in app_state.gmail_messages:
        if msg.senderEmail in request.addresses:
            return msg.id

    return app_state.gmail_messages[0].id


if __name__ == "__main__":
    print("🚀 Starting Gmail API Mock Server")
    print(f"🌐 Server will run on http://{settings.host}:{settings.port}")
    uvicorn.run(app, host=settings.host, port=settings.port, ws="none")
