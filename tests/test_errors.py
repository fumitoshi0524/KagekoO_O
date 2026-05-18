from __future__ import annotations

from qaoa.cli.errors import classify_error, format_error, ErrorKind


def test_classify_auth_error():
    kind, msg = classify_error(Exception("401 Unauthorized"))
    assert kind == ErrorKind.AUTH
    assert "API key" in msg


def test_classify_quota_error():
    kind, msg = classify_error(Exception("insufficient_quota"))
    assert kind in (ErrorKind.QUOTA, ErrorKind.RATE_LIMIT)


def test_classify_rate_limit():
    kind, msg = classify_error(Exception("rate limit exceeded"))
    assert kind == ErrorKind.RATE_LIMIT


def test_classify_connection_error():
    kind, msg = classify_error(ConnectionError("connection refused"))
    assert kind == ErrorKind.CONNECTION


def test_classify_timeout():
    kind, msg = classify_error(TimeoutError("timed out"))
    assert kind == ErrorKind.TIMEOUT


def test_classify_parse_error():
    kind, msg = classify_error(Exception("json parse error: unexpected token"))
    assert kind == ErrorKind.PARSE


def test_classify_config_error():
    kind, msg = classify_error(Exception("Set KAGEKO_PROVIDER to configure"))
    assert kind == ErrorKind.CONFIG


def test_classify_unknown_error():
    kind, msg = classify_error(Exception("something completely unexpected happened"))
    assert kind == ErrorKind.UNKNOWN


def test_format_error_includes_detail():
    result = format_error(ValueError("401 Unauthorized: bad key"))
    assert "AUTH" in result
    assert "bad key" in result


def test_format_unknown_error():
    result = format_error(ValueError("random stuff"))
    assert "ERROR" in result
    assert "random stuff" in result
