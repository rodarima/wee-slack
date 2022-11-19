from unittest.mock import MagicMock, patch

import pytest
import weechat

from slack.http import HttpError, http_request
from slack.task import FutureProcess, FutureTimer, weechat_task_cb


@patch.object(weechat, "hook_process_hashtable")
def test_http_request_success(mock_method: MagicMock):
    url = "http://example.com"
    options = {"option": "1"}
    timeout = 123
    coroutine = http_request(url, options, timeout)
    future = coroutine.send(None)
    assert isinstance(future, FutureProcess)

    mock_method.assert_called_once_with(
        f"url:{url}",
        {**options, "header": "1"},
        timeout,
        weechat_task_cb.__name__,
        future.id,
    )

    response = "response"
    body = f"HTTP/2 200\r\n\r\n{response}"

    with pytest.raises(StopIteration) as excinfo:
        coroutine.send(("", 0, body, ""))
    assert excinfo.value.value == response


def test_http_request_error_process_return_code():
    url = "http://example.com"
    coroutine = http_request(url, {}, 0, max_retries=0)
    assert isinstance(coroutine.send(None), FutureProcess)

    with pytest.raises(HttpError) as excinfo:
        coroutine.send(("", -2, "", ""))

    assert excinfo.value.url == url
    assert excinfo.value.return_code == -2
    assert excinfo.value.http_status == 0
    assert excinfo.value.error == ""


def test_http_request_error_process_stderr():
    url = "http://example.com"
    coroutine = http_request(url, {}, 0, max_retries=0)
    assert isinstance(coroutine.send(None), FutureProcess)

    with pytest.raises(HttpError) as excinfo:
        coroutine.send(("", 0, "", "err"))

    assert excinfo.value.url == url
    assert excinfo.value.return_code == 0
    assert excinfo.value.http_status == 0
    assert excinfo.value.error == "err"


def test_http_request_error_process_http():
    url = "http://example.com"
    coroutine = http_request(url, {}, 0, max_retries=0)
    assert isinstance(coroutine.send(None), FutureProcess)

    response = "response"
    body = f"HTTP/2 400\r\n\r\n{response}"

    with pytest.raises(HttpError) as excinfo:
        coroutine.send(("", 0, body, ""))

    assert excinfo.value.url == url
    assert excinfo.value.return_code == 0
    assert excinfo.value.http_status == 400
    assert excinfo.value.error == response


def test_http_request_error_retry_success():
    url = "http://example.com"
    coroutine = http_request(url, {}, 0, max_retries=2)
    assert isinstance(coroutine.send(None), FutureProcess)

    assert isinstance(coroutine.send(("", -2, "", "")), FutureTimer)
    assert isinstance(coroutine.send((0,)), FutureProcess)

    response = "response"
    body = f"HTTP/2 200\r\n\r\n{response}"

    with pytest.raises(StopIteration) as excinfo:
        coroutine.send(("", 0, body, ""))
    assert excinfo.value.value == response


def test_http_request_error_retry_error():
    url = "http://example.com"
    coroutine = http_request(url, {}, 0, max_retries=2)
    assert isinstance(coroutine.send(None), FutureProcess)

    assert isinstance(coroutine.send(("", -2, "", "")), FutureTimer)
    assert isinstance(coroutine.send((0,)), FutureProcess)
    assert isinstance(coroutine.send(("", -2, "", "")), FutureTimer)
    assert isinstance(coroutine.send((0,)), FutureProcess)

    with pytest.raises(HttpError) as excinfo:
        coroutine.send(("", -2, "", ""))

    assert excinfo.value.url == url
    assert excinfo.value.return_code == -2
    assert excinfo.value.http_status == 0
    assert excinfo.value.error == ""


@patch.object(weechat, "hook_timer")
def test_http_request_ratelimit(mock_method: MagicMock):
    url = "http://example.com"
    coroutine = http_request(url, {}, 0)
    assert isinstance(coroutine.send(None), FutureProcess)

    body = "HTTP/2 429\r\nRetry-After: 12\r\n\r\n"

    timer = coroutine.send(("", 0, body, ""))
    assert isinstance(timer, FutureTimer)

    mock_method.assert_called_once_with(12000, 0, 1, weechat_task_cb.__name__, timer.id)

    assert isinstance(coroutine.send((0,)), FutureProcess)

    with pytest.raises(StopIteration):
        coroutine.send(("", 0, "HTTP/2 200\r\n\r\n", ""))