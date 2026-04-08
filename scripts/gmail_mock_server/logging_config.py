"""
Centralized logging configuration for Gmail Mock Server.
Uses dictConfig for clean, maintainable logging setup.
"""
import logging.config
import os
from typing import Dict, Any

NODE_ENV = os.getenv("NODE_ENV", "production").lower()
IS_DEV = NODE_ENV == "development"

LOGGING_CONFIG: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "simple": {
            "format": "%(levelname)s: %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG" if IS_DEV else "ERROR",
            "formatter": "standard" if IS_DEV else "simple",
            "stream": "ext://sys.stdout"
        }
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console"],
            "level": "DEBUG" if IS_DEV else "ERROR",
            "propagate": False
        },
        "uvicorn": {
            "handlers": ["console"],
            "level": "INFO" if IS_DEV else "ERROR",
            "propagate": False
        },
        "uvicorn.access": {
            "handlers": ["console"],
            "level": "INFO" if IS_DEV else "ERROR", 
            "propagate": False
        }
    }
}

def setup_logging():
    """Apply the logging configuration."""
    logging.config.dictConfig(LOGGING_CONFIG)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the configured setup."""
    return logging.getLogger(name)
