"""Unit tests for the Skybrush Viewer bridge request timeout."""

from io import BytesIO
from socket import timeout as SocketTimeoutError
from unittest import mock

import pytest
from sbstudio.viewer_bridge import SkybrushViewerBridge, SkybrushViewerError


def _bridge():
    bridge = SkybrushViewerBridge()
    bridge._discovery.discover = mock.Mock(return_value="http://127.0.0.1:1234")
    return bridge


def _response(payload: bytes):
    response = mock.Mock()
    response.__enter__ = mock.Mock(return_value=BytesIO(payload))
    response.__exit__ = mock.Mock(return_value=False)
    return response


def test_request_passes_timeout_to_urlopen():
    bridge = _bridge()
    with mock.patch(
        "sbstudio.viewer_bridge.urlopen",
        return_value=_response(b'{"result": true}'),
    ) as urlopen:
        assert bridge.check_running() is True
    _, kwargs = urlopen.call_args
    assert kwargs.get("timeout") == 30


def test_timeout_is_reported_as_viewer_error():
    bridge = _bridge()
    with mock.patch(
        "sbstudio.viewer_bridge.urlopen",
        side_effect=SocketTimeoutError("timed out"),
    ):
        with pytest.raises(SkybrushViewerError, match="Timed out"):
            bridge.check_running()
