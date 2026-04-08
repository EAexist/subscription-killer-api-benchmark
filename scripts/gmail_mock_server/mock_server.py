import logging
from typing import Optional

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import centralized logging configuration
from logging_config import setup_logging, get_logger

# Setup logging configuration
setup_logging()
logger = get_logger(__name__)

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
        status="healthy", messages_per_request=app_state.message_selector.chunk_size
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
    selected_messages = app_state.message_selector.select_messages()

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
    messages = app_state.message_selector.get_messages(message_ids)

    return BatchGetResponse(messages=messages)


@app.post("/messages/first")
async def get_first_message_id(request: FirstMessageIdRequest):
    """
    Gmail API endpoint for getting first message ID by addresses.
    Returns the first message ID found from the given addresses.
    """
    return app_state.message_selector.get_first_message_id(request.addresses)


if __name__ == "__main__":
    logger.info("🚀 Starting Gmail API Mock Server")
    logger.info(f"🌐 Server will run on http://{settings.host}:{settings.port}")
    uvicorn.run(app, host=settings.host, port=settings.port, ws="none")
