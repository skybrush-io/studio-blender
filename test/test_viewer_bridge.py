"""Unit tests for the Skybrush Viewer bridge request timeout."""

import socket
import time
from io import BytesIO
from socket import timeout as SocketTimeoutError
from unittest import mock

import pytest
from sbstudio.viewer_bridge import SkybrushViewerBridge, SkybrushViewerError


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
        "sbstudio.viewer_bridge.urlopen",
        return_value=_response(b'{"result": true}'),
    ) as urlopen:
        assert bridge.check_running() is True
    _, kwargs = urlopen.call_args
    assert kwargs.get("timeout") == 30


def test_timeout_is_reported_as_viewer_error():
    bridge = _bridge(["http://127.0.0.1:1234"])
    with mock.patch(
        "sbstudio.viewer_bridge.urlopen",
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
            "sbstudio.viewer_bridge.urlopen",
            return_value=_response(b'{"result": true}'),
        ) as urlopen:
            assert bridge.check_running() is True
        _, kwargs = urlopen.call_args
        assert kwargs.get("timeout") == 10
    finally:
        socket.setdefaulttimeout(old)


def test_longer_socket_default_is_capped_at_30():
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(60)
    try:
        bridge = _bridge(["http://127.0.0.1:1234"])
        with mock.patch(
            "sbstudio.viewer_bridge.urlopen",
            return_value=_response(b'{"result": true}'),
        ) as urlopen:
            assert bridge.check_running() is True
        _, kwargs = urlopen.call_args
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

    with mock.patch("sbstudio.viewer_bridge.urlopen", side_effect=fake_urlopen):
        assert bridge.check_running() is True
    assert calls == [
        "http://127.0.0.1:1234/api/v1/ping",
        "http://192.168.1.5:1234/api/v1/ping",
    ]


def test_timeout_does_not_retry_the_same_url():
    bridge = _bridge(["http://127.0.0.1:1234", "http://127.0.0.1:1234"])
    with mock.patch(
        "sbstudio.viewer_bridge.urlopen",
        side_effect=SocketTimeoutError("timed out"),
    ) as urlopen:
        with pytest.raises(SkybrushViewerError, match="Timed out"):
            bridge.check_running()
    assert urlopen.call_count == 1


def test_non_local_viewer_url_is_rejected():
    bridge = _bridge(["http://8.8.8.8:1234"])
    with mock.patch("sbstudio.viewer_bridge.urlopen") as urlopen:
        with pytest.raises(SkybrushViewerError, match="not a local address"):
            bridge.check_running()
    urlopen.assert_not_called()


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
            "sbstudio.viewer_bridge.urlopen",
            return_value=TricklingResponse(),
        ):
            with pytest.raises(SkybrushViewerError, match="Timed out"):
                bridge.check_running()
    finally:
        socket.setdefaulttimeout(old)
