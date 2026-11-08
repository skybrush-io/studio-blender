"""Unit tests for the Skybrush Viewer bridge request timeout."""

import socket
import time
from io import BytesIO
from socket import timeout as SocketTimeoutError
from unittest import mock
from urllib.error import URLError
from urllib.request import Request

import pytest
from sbstudio.viewer_bridge import (
    SkybrushViewerBridge,
    SkybrushViewerError,
    _ViewerRedirectHandler,
)


def _bridge(urls):
    bridge = SkybrushViewerBridge()
    urls = list(urls)

    def _discover(force=False):
        if len(urls) > 1:
            return urls.pop(0)
        return urls[0]

    bridge._discovery.discover = mock.Mock(side_effect=_discover)
    return bridge


def _response(payload: bytes):
    response = mock.Mock()
    response.__enter__ = mock.Mock(return_value=BytesIO(payload))
    response.__exit__ = mock.Mock(return_value=False)
    return response


def test_request_passes_timeout_to_urlopen():
    bridge = _bridge(["http://127.0.0.1:1234"])
    with mock.patch(
        "sbstudio.viewer_bridge._open_viewer_request",
        return_value=_response(b'{"result": true}'),
    ) as open_request:
        assert bridge.check_running() is True
    _, kwargs = open_request.call_args
    assert kwargs.get("timeout") == 30


def test_timeout_is_reported_as_viewer_error():
    bridge = _bridge(["http://127.0.0.1:1234"])
    with mock.patch(
        "sbstudio.viewer_bridge._open_viewer_request",
        side_effect=SocketTimeoutError("timed out"),
    ):
        with pytest.raises(SkybrushViewerError, match="Timed out"):
            bridge.check_running()


def test_shorter_socket_default_is_honored():
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(10)
    try:
        bridge = _bridge(["http://127.0.0.1:1234"])
        with mock.patch(
            "sbstudio.viewer_bridge._open_viewer_request",
            return_value=_response(b'{"result": true}'),
        ) as open_request:
            assert bridge.check_running() is True
        _, kwargs = open_request.call_args
        assert kwargs.get("timeout") == 10
    finally:
        socket.setdefaulttimeout(old)


def test_longer_socket_default_is_capped_at_30():
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(60)
    try:
        bridge = _bridge(["http://127.0.0.1:1234"])
        with mock.patch(
            "sbstudio.viewer_bridge._open_viewer_request",
            return_value=_response(b'{"result": true}'),
        ) as open_request:
            assert bridge.check_running() is True
        _, kwargs = open_request.call_args
        assert kwargs.get("timeout") == 30
    finally:
        socket.setdefaulttimeout(old)


def test_timeout_retries_against_a_different_url():
    bridge = _bridge(["http://127.0.0.1:1234", "http://192.168.1.5:1234"])
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(request.full_url)
        if "127.0.0.1" in request.full_url:
            raise SocketTimeoutError("timed out")
        return _response(b'{"result": true}')

    with mock.patch(
        "sbstudio.viewer_bridge._open_viewer_request", side_effect=fake_urlopen
    ):
        assert bridge.check_running() is True
    assert calls == [
        "http://127.0.0.1:1234/api/v1/ping",
        "http://192.168.1.5:1234/api/v1/ping",
    ]
    assert bridge._discovery.discover.call_args_list == [
        mock.call(force=False),
        mock.call(force=True),
    ]


def test_timeout_does_not_retry_the_same_url():
    bridge = _bridge(["http://127.0.0.1:1234", "http://127.0.0.1:1234"])
    with mock.patch(
        "sbstudio.viewer_bridge._open_viewer_request",
        side_effect=SocketTimeoutError("timed out"),
    ) as open_request:
        with pytest.raises(SkybrushViewerError, match="Timed out"):
            bridge.check_running()
    assert open_request.call_count == 1


def test_non_local_viewer_url_is_rejected():
    bridge = _bridge(["http://8.8.8.8:1234"])
    with mock.patch("sbstudio.viewer_bridge._open_viewer_request") as open_request:
        with pytest.raises(SkybrushViewerError, match="not a local address"):
            bridge.check_running()
    open_request.assert_not_called()


def test_trickling_response_hits_the_overall_deadline():
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(0.3)
    try:
        bridge = _bridge(["http://127.0.0.1:1234"])

        class TricklingResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, size=-1):
                time.sleep(0.15)
                return b"x"

        with mock.patch(
            "sbstudio.viewer_bridge._open_viewer_request",
            return_value=TricklingResponse(),
        ):
            with pytest.raises(SkybrushViewerError, match="Timed out"):
                bridge.check_running()
    finally:
        socket.setdefaulttimeout(old)


def test_urlerror_wrapping_timeout_retries_against_a_different_url():
    bridge = _bridge(["http://127.0.0.1:1234", "http://192.168.1.5:1234"])
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(request.full_url)
        if "127.0.0.1" in request.full_url:
            raise URLError(SocketTimeoutError("timed out"))
        return _response(b'{"result": true}')

    with mock.patch(
        "sbstudio.viewer_bridge._open_viewer_request", side_effect=fake_urlopen
    ):
        assert bridge.check_running() is True
    assert calls == [
        "http://127.0.0.1:1234/api/v1/ping",
        "http://192.168.1.5:1234/api/v1/ping",
    ]


def test_urlerror_wrapping_timeout_does_not_retry_the_same_url():
    bridge = _bridge(["http://127.0.0.1:1234", "http://127.0.0.1:1234"])
    with mock.patch(
        "sbstudio.viewer_bridge._open_viewer_request",
        side_effect=URLError(SocketTimeoutError("timed out")),
    ) as open_request:
        with pytest.raises(SkybrushViewerError, match="Timed out"):
            bridge.check_running()
    assert open_request.call_count == 1


def test_redirect_to_public_host_is_rejected():
    handler = _ViewerRedirectHandler()
    request = Request("http://127.0.0.1:1234/api/v1/ping")
    with pytest.raises(SkybrushViewerError, match="non-local address"):
        handler.redirect_request(
            request, None, 302, "Found", {}, "http://169.254.169.254/latest/"
        )


def test_redirect_to_local_host_is_allowed():
    handler = _ViewerRedirectHandler()
    request = Request("http://127.0.0.1:1234/api/v1/ping")
    result = handler.redirect_request(
        request, None, 302, "Found", {}, "http://127.0.0.1:5678/api/v1/ping"
    )
    assert result.full_url == "http://127.0.0.1:5678/api/v1/ping"


def test_slow_hostname_resolution_is_bounded():
    bridge = _bridge(["http://viewer.local:1234"])

    def slow_getaddrinfo(*args):
        time.sleep(5)
        return [(socket.AF_INET, None, None, None, ("127.0.0.1", 0))]

    start = time.monotonic()
    with mock.patch("sbstudio.viewer_bridge.getaddrinfo", side_effect=slow_getaddrinfo):
        with pytest.raises(SkybrushViewerError, match="not a local address"):
            bridge.check_running()
    assert time.monotonic() - start < 4
