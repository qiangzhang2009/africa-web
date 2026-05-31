"""Structured logging setup with request ID tracing."""
import logging
import sys
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# ─── Logger factory ───────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def setup_logging(debug: bool = False) -> None:
    """Configure root logger with structured format."""
    level = logging.DEBUG if debug else logging.INFO

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)

    # File handler (rotating)
    try:
        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler(
            "logs/app.log",
            maxBytes=10_000_000,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        handlers = [console_handler, file_handler]
    except Exception:
        handlers = [console_handler]

    logging.basicConfig(level=level, handlers=handlers, force=True)

    # Reduce noise from third-party libraries
    for lib in ["uvicorn.access", "httpx", "httpcore", "urllib3"]:
        logging.getLogger(lib).setLevel(logging.WARNING)


# ─── Request ID middleware ───────────────────────────────────────────────────

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects X-Request-ID header for distributed tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Add request ID to logging context
        logger = get_logger("http")
        start_time = time.time()

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                f"{request.method} {request.url.path} | "
                f"status={response.status_code} | "
                f"duration={duration_ms:.1f}ms | "
                f"request_id={request_id}"
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"{request.method} {request.url.path} | "
                f"error={str(e)} | "
                f"duration={duration_ms:.1f}ms | "
                f"request_id={request_id}"
            )
            raise
