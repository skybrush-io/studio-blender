"""Unit tests for the Skybrush Viewer bridge request timeout."""

import errno
import socket
import threading
import time
from io import BytesIO
from socket import timeout as SocketTimeoutError
from unittest import mock
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest
from sbstudio.viewer_bridge import (
    SkybrushViewerBridge,
    SkybrushViewerError,
    _ViewerRedirectHandler,
)


def _bridge(urls):
    """Builds a bridge whose discovery returns the given URLs."""
    bridge = SkybrushViewerBridge()
    urls = list(urls)

    def _discover(force=False, expected_url=None):
        """Returns the next canned URL."""
        if len(urls) > 1:
            return urls.pop(0)
        return urls[0]

    bridge._discovery.discover = mock.Mock(side_effect=_discover)
    return bridge


def _response(payload: bytes):
    """Builds a context-manager response wrapping the payload."""
    response = mock.Mock()
    response.__enter__ = mock.Mock(return_value=BytesIO(payload))
    response.__exit__ = mock.Mock(return_value=False)
    return response


def test_request_passes_timeout_to_urlopen():
    """urlopen receives the per-request timeout."""
    bridge = _bridge(["http://127.0.0.1:1234"])
    start = time.monotonic()
    with mock.patch(
        "sbstudio.viewer_bridge._open_viewer_request",
        return_value=_response(b'{"result": true}'),
    ) as open_request:
        assert bridge.check_running() is True
    _, kwargs = open_request.call_args
    deadline = open_request.call_args.args[1]
    assert deadline is not None
    assert start + 30 <= deadline < start + 32


def test_timeout_is_reported_as_viewer_error():
    """A timeout surfaces as a SkybrushViewerError."""
    bridge = _bridge(["http://127.0.0.1:1234"])
    with mock.patch(
        "sbstudio.viewer_bridge._open_viewer_request",
        side_effect=SocketTimeoutError("timed out"),
    ):
        with pytest.raises(SkybrushViewerError, match="Timed out"):
            bridge.check_running()


def test_shorter_socket_default_is_honored():
    """A shorter socket default timeout is honored."""
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(10)
    try:
        bridge = _bridge(["http://127.0.0.1:1234"])
        start = time.monotonic()
        with mock.patch(
            "sbstudio.viewer_bridge._open_viewer_request",
            return_value=_response(b'{"result": true}'),
        ) as open_request:
            assert bridge.check_running() is True
        _, kwargs = open_request.call_args
        deadline = open_request.call_args.args[1]
        assert deadline is not None
        assert start + 10 <= deadline < start + 12
    finally:
        socket.setdefaulttimeout(old)


def test_longer_socket_default_is_capped_at_30():
    """A longer socket default is capped at 30 seconds."""
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(60)
    try:
        bridge = _bridge(["http://127.0.0.1:1234"])
        start = time.monotonic()
        with mock.patch(
            "sbstudio.viewer_bridge._open_viewer_request",
            return_value=_response(b'{"result": true}'),
        ) as open_request:
            assert bridge.check_running() is True
        _, kwargs = open_request.call_args
        deadline = open_request.call_args.args[1]
        assert deadline is not None
        assert start + 30 <= deadline < start + 32
    finally:
        socket.setdefaulttimeout(old)


def test_timeout_retries_against_a_different_url():
    """A timeout retries once against a different Viewer URL."""
    bridge = _bridge(["http://127.0.0.1:1234", "http://192.168.1.5:1234"])
    calls = []

    def fake_urlopen(request, deadline=None):
        """Times out for the first URL, succeeds for the second."""
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
        mock.call(force=False, expected_url=None),
        mock.call(force=True, expected_url="http://127.0.0.1:1234"),
    ]


def test_timeout_retry_invalidates_raw_cached_url():
    """A trailing-slash LOCATION is invalidated verbatim on timeout retry."""
    bridge = _bridge(["http://127.0.0.1:1234/", "http://192.168.1.5:1234"])
    calls = []

    def fake_urlopen(request, deadline=None):
        """Times out for the first URL, succeeds for the second."""
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
        mock.call(force=False, expected_url=None),
        mock.call(force=True, expected_url="http://127.0.0.1:1234/"),
    ]


def test_connection_refused_retry_passes_failed_url():
    """An ECONNREFUSED retry only clears the URL that refused."""
    bridge = _bridge(["http://127.0.0.1:1234", "http://192.168.1.5:1234"])
    calls = []

    def fake_urlopen(request, deadline=None):
        """Refuses the first URL, succeeds for the second."""
        calls.append(request.full_url)
        if "127.0.0.1" in request.full_url:
            raise URLError(
                ConnectionRefusedError(errno.ECONNREFUSED, "Connection refused")
            )
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
        mock.call(force=False, expected_url=None),
        mock.call(force=True, expected_url="http://127.0.0.1:1234"),
    ]


def test_timed_out_open_closes_the_connection():
    """A timed-out open shuts down its socket so no thread lingers."""
    from sbstudio.viewer_bridge import _open_viewer_request

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    closed = threading.Event()

    def _serve():
        """Trickles header bytes, then records when the client disconnects."""
        conn, _ = server.accept()
        try:
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n")
            for _ in range(100):
                conn.sendall(b"X-Trickle: 1\r\n")
                time.sleep(0.2)
        except OSError:
            pass
        finally:
            conn.settimeout(2)
            try:
                while conn.recv(4096):
                    pass
            except OSError:
                pass
            closed.set()
            conn.close()
            server.close()

    threading.Thread(target=_serve, daemon=True).start()
    request = Request(f"http://127.0.0.1:{port}/api/v1/ping")
    start = time.monotonic()
    with pytest.raises(SocketTimeoutError, match="timed out"):
        _open_viewer_request(request, time.monotonic() + 0.5)
    assert time.monotonic() - start < 2
    assert closed.wait(timeout=3)


def test_timeout_does_not_retry_the_same_url():
    """A timeout does not retry the same Viewer URL."""
    bridge = _bridge(["http://127.0.0.1:1234", "http://127.0.0.1:1234"])
    with mock.patch(
        "sbstudio.viewer_bridge._open_viewer_request",
        side_effect=SocketTimeoutError("timed out"),
    ) as open_request:
        with pytest.raises(SkybrushViewerError, match="Timed out"):
            bridge.check_running()
    assert open_request.call_count == 1


def test_non_local_viewer_url_is_rejected():
    """A non-local Viewer URL is rejected without a request."""
    bridge = _bridge(["http://8.8.8.8:1234"])
    with mock.patch("sbstudio.viewer_bridge._open_viewer_request") as open_request:
        with pytest.raises(SkybrushViewerError, match="not a local address"):
            bridge.check_running()
    open_request.assert_not_called()


def test_trickling_response_hits_the_overall_deadline():
    """A trickling response is cut off by the overall deadline."""
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(0.3)
    try:
        bridge = _bridge(["http://127.0.0.1:1234"])

        class TricklingResponse:
            """A response that yields one byte per read, forever."""

            def __enter__(self):
                """Returns the response itself."""
                return self

            def __exit__(self, *args):
                """Ignores the context exit."""
                return False

            def read(self, size=-1):
                """Sleeps briefly, then returns one byte."""
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
    """A URLError-wrapped timeout retries against a different URL."""
    bridge = _bridge(["http://127.0.0.1:1234", "http://192.168.1.5:1234"])
    calls = []

    def fake_urlopen(request, deadline=None):
        """Times out for the first URL, succeeds for the second."""
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
    """A URLError-wrapped timeout does not retry the same URL."""
    bridge = _bridge(["http://127.0.0.1:1234", "http://127.0.0.1:1234"])
    with mock.patch(
        "sbstudio.viewer_bridge._open_viewer_request",
        side_effect=URLError(SocketTimeoutError("timed out")),
    ) as open_request:
        with pytest.raises(SkybrushViewerError, match="Timed out"):
            bridge.check_running()
    assert open_request.call_count == 1


def test_redirect_to_public_host_is_rejected():
    """A redirect to a public host is rejected."""
    handler = _ViewerRedirectHandler()
    request = Request("http://127.0.0.1:1234/api/v1/ping")
    with pytest.raises(SkybrushViewerError, match="non-local address"):
        handler.redirect_request(
            request, None, 302, "Found", {}, "http://169.254.169.254/latest/"
        )


def test_redirect_to_local_host_is_allowed():
    """A redirect to a local host is followed."""
    handler = _ViewerRedirectHandler()
    request = Request("http://127.0.0.1:1234/api/v1/ping")
    result = handler.redirect_request(
        request, None, 302, "Found", {}, "http://127.0.0.1:5678/api/v1/ping"
    )
    assert result.full_url == "http://127.0.0.1:5678/api/v1/ping"


def test_slow_hostname_resolution_is_bounded():
    """A slow DNS lookup is bounded by the resolver timeout."""
    bridge = _bridge(["http://viewer.local:1234"])

    def slow_getaddrinfo(*args):
        """Pretends DNS takes five seconds."""
        time.sleep(5)
        return [(socket.AF_INET, None, None, None, ("127.0.0.1", 0))]

    start = time.monotonic()
    with mock.patch("sbstudio.viewer_bridge.getaddrinfo", side_effect=slow_getaddrinfo):
        with pytest.raises(SkybrushViewerError, match="not a local address"):
            bridge.check_running()
    assert time.monotonic() - start < 4


def test_slow_header_read_hits_the_deadline():
    """A slow header read is cut off by the deadline."""
    from sbstudio.viewer_bridge import _open_viewer_request

    request = Request("http://127.0.0.1:1234/api/v1/ping")

    def slow_open(req, timeout=None):
        """Pretends the open takes five seconds."""
        time.sleep(5)
        return _response(b'{"result": true}')

    opener = mock.Mock()
    opener.open.side_effect = slow_open
    start = time.monotonic()
    with mock.patch("sbstudio.viewer_bridge.build_opener", return_value=opener):
        with pytest.raises(SocketTimeoutError, match="timed out"):
            _open_viewer_request(request, time.monotonic() + 0.5)
    assert time.monotonic() - start < 2


def test_invalidate_keeps_newer_cached_url():
    """Invalidating a stale URL keeps a newer cached URL."""
    from sbstudio.viewer_bridge import SSDPAppDiscovery

    discovery = SSDPAppDiscovery("urn:test:1")
    discovery._url = "http://192.168.1.5:1234"
    discovery._last_checked_at = time.monotonic()
    discovery.invalidate("http://127.0.0.1:1234")
    assert discovery._url == "http://192.168.1.5:1234"
    discovery.invalidate("http://192.168.1.5:1234")
    assert discovery._url is None


def test_failed_request_keeps_newer_cached_url():
    """A failed request keeps a newer cached URL."""
    bridge = _bridge(["http://127.0.0.1:1234"])
    bridge._discovery._url = "http://127.0.0.1:1234"
    bridge._discovery._last_checked_at = time.monotonic()

    def fake_open(request, deadline=None):
        """Caches a newer URL, then fails with a server error."""
        # A newer validation caches URL2 while this request is in flight
        bridge._discovery._url = "http://192.168.1.5:1234"
        bridge._discovery._last_checked_at = time.monotonic()
        raise HTTPError(request.full_url, 500, "Server Error", {}, None)

    with mock.patch(
        "sbstudio.viewer_bridge._open_viewer_request", side_effect=fake_open
    ):
        with pytest.raises(SkybrushViewerError, match="unexpected error"):
            bridge.check_running()
    assert bridge._discovery._url == "http://192.168.1.5:1234"
