import time
import logging
from typing import Any
from flask import Request, Response, jsonify
from core.errors import AgenticSuiteError

logger = logging.getLogger(__name__)

def setup_middleware(app: Any) -> None:
    """Configures global error handlers and request logging."""

    @app.errorhandler(AgenticSuiteError)
    def handle_suite_error(e: AgenticSuiteError) -> Response:
        logger.error("Suite Error: %s", str(e))
        response = jsonify({"status": "error", "message": str(e)})
        response.status_code = 400
        return response

    @app.errorhandler(Exception)
    def handle_generic_error(e: Exception) -> Response:
        logger.error("Unhandled Exception: %s", str(e), exc_info=True)
        response = jsonify({"status": "error", "message": "Internal Server Error"})
        response.status_code = 500
        return response

    @app.before_request
    def log_request_info() -> None:
        logger.info("Request: %s %s", Request.method, Request.path)
        Request.start_time = time.time() # type: ignore

    @app.after_request
    def log_response_info(response: Response) -> Response:
        duration = time.time() - getattr(Request, "start_time", time.time())
        logger.info("Response: %s (%.2fms)", response.status, duration * 1000)
        return response
