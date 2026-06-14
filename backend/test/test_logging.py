"""JSON logging unit tests."""

from __future__ import annotations

import json
import logging
from io import StringIO

from core.logging import JsonFormatter, configure_logging
from core.settings import Settings, clear_settings_cache


def test_json_formatter_emits_required_keys():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    payload = json.loads(formatter.format(record))
    assert "ts" in payload
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.logger"
    assert payload["msg"] == "hello"


def test_json_formatter_propagates_extra():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    test_logger = logging.getLogger("test.extra")
    test_logger.handlers.clear()
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.INFO)
    test_logger.propagate = False

    test_logger.info("hi", extra={"product_id": "abc"})
    payload = json.loads(stream.getvalue().strip())
    assert payload["product_id"] == "abc"


def test_json_formatter_handles_exception():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    test_logger = logging.getLogger("test.exception")
    test_logger.handlers.clear()
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.ERROR)
    test_logger.propagate = False

    try:
        raise ValueError("boom")
    except ValueError:
        test_logger.exception("failed")

    payload = json.loads(stream.getvalue().strip())
    assert isinstance(payload["exc_info"], str)
    assert payload["exc_info"]


def test_configure_logging_idempotent():
    clear_settings_cache()
    settings = Settings(log_level="INFO")
    configure_logging(settings)
    root = logging.getLogger()
    handler_count = len(root.handlers)
    configure_logging(settings)
    assert len(root.handlers) == handler_count
