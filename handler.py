import base64
import binascii
import json
import logging
import os
from collections.abc import Mapping

from gpxpy.gpx import GPXException

from service import SUPPORTED_LANGUAGES, SUPPORTED_THEMES, generate_story


logger = logging.getLogger(__name__)

DEFAULT_MAX_GPX_SIZE_BYTES = 5 * 1024 * 1024


def _configured_max_gpx_size() -> int:
    configured = os.getenv("GPX_MAX_SIZE_BYTES")
    if configured is None:
        return DEFAULT_MAX_GPX_SIZE_BYTES
    try:
        max_size = int(configured)
    except ValueError as exc:
        raise RuntimeError("GPX_MAX_SIZE_BYTES must be a positive integer") from exc
    if max_size <= 0:
        raise RuntimeError("GPX_MAX_SIZE_BYTES must be a positive integer")
    return max_size


MAX_GPX_SIZE_BYTES = _configured_max_gpx_size()
SUPPORTED_METHOD = "POST"
SUPPORTED_PATH = "/v1/generate"
SUPPORTED_CONTENT_TYPE = "application/gpx+xml"


def _error_response(status_code: int, code: str, message: str) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "isBase64Encoded": False,
        "body": json.dumps({"code": code, "message": message}),
    }


def _get_header(headers: Mapping, name: str):
    for key, value in headers.items():
        if isinstance(key, str) and key.lower() == name.lower():
            return value
    return None


def lambda_handler(event, context):
    if not isinstance(event, Mapping) or event.get("version") != "2.0":
        return _error_response(400, "INVALID_REQUEST", "Expected an HTTP API v2 request.")

    request_context = event.get("requestContext")
    http_context = request_context.get("http") if isinstance(request_context, Mapping) else None
    method = http_context.get("method") if isinstance(http_context, Mapping) else None
    path = event.get("rawPath")
    if not isinstance(method, str) or not isinstance(path, str):
        return _error_response(400, "INVALID_REQUEST", "The request is malformed.")
    if method != SUPPORTED_METHOD:
        return _error_response(405, "METHOD_NOT_ALLOWED", "Only POST is supported.")
    if path != SUPPORTED_PATH:
        return _error_response(404, "NOT_FOUND", "Route not found.")

    headers = event.get("headers", {})
    if not isinstance(headers, Mapping):
        return _error_response(400, "INVALID_REQUEST", "The request is malformed.")
    content_type = _get_header(headers, "Content-Type")
    if not isinstance(content_type, str):
        return _error_response(
            415,
            "UNSUPPORTED_MEDIA_TYPE",
            "Content-Type must be application/gpx+xml.",
        )
    media_type = content_type.split(";", 1)[0].strip().lower()
    if media_type != SUPPORTED_CONTENT_TYPE:
        return _error_response(
            415,
            "UNSUPPORTED_MEDIA_TYPE",
            "Content-Type must be application/gpx+xml.",
        )

    query_parameters = event.get("queryStringParameters")
    if query_parameters is None:
        query_parameters = {}
    if not isinstance(query_parameters, Mapping):
        return _error_response(400, "INVALID_REQUEST", "The request is malformed.")
    theme = query_parameters.get("theme", "forest")
    lang = query_parameters.get("lang", "en")
    if (
        not isinstance(theme, str)
        or theme not in SUPPORTED_THEMES
        or not isinstance(lang, str)
        or lang not in SUPPORTED_LANGUAGES
    ):
        return _error_response(
            400,
            "INVALID_PARAMETERS",
            "The requested theme or language is not supported.",
        )

    body = event.get("body")
    is_base64_encoded = event.get("isBase64Encoded")
    if not isinstance(body, str) or not isinstance(is_base64_encoded, bool):
        return _error_response(400, "INVALID_REQUEST", "The request body is malformed.")
    if not body:
        return _error_response(400, "EMPTY_BODY", "The GPX body must not be empty.")

    try:
        if is_base64_encoded:
            gpx_content = base64.b64decode(body.encode("ascii"), validate=True)
        else:
            gpx_content = body.encode("utf-8")
    except (binascii.Error, UnicodeEncodeError):
        return _error_response(400, "INVALID_BODY_ENCODING", "The request body encoding is invalid.")

    if not gpx_content.strip():
        return _error_response(400, "EMPTY_BODY", "The GPX body must not be empty.")
    if len(gpx_content) > MAX_GPX_SIZE_BYTES:
        return _error_response(
            413,
            "PAYLOAD_TOO_LARGE",
            "The GPX payload exceeds the configured size limit.",
        )

    try:
        png_content = generate_story(gpx_content, theme=theme, lang=lang)
        if not isinstance(png_content, bytes):
            raise TypeError("The story service returned a non-bytes result.")
    except (GPXException, ValueError):
        return _error_response(
            422,
            "INVALID_GPX",
            "The GPX content is invalid or could not be processed.",
        )
    except Exception:
        logger.error("Unexpected error while generating a GPX story.")
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred.")

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "image/png"},
        "isBase64Encoded": True,
        "body": base64.b64encode(png_content).decode("ascii"),
    }
