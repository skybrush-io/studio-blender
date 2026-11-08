"""Classes related to discovering a running Skybrush Viewer instance on the
current machine and for posting data to it.
"""

import ipaddress
import threading
from datetime import datetime
from email.utils import parsedate_to_datetime
from errno import ECONNREFUSED, ENETUNREACH
from json import loads
from socket import (
    AF_INET,
    IPPROTO_UDP,
    SOCK_DGRAM,
    getaddrinfo,
    getdefaulttimeout,
    socket,
)
from socket import (
    timeout as SocketTimeoutError,
)
from time import monotonic
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

__all__ = ("SkybrushViewerBridge",)


_VIEWER_TIMEOUT = 30
"""Maximum number of seconds to wait for a response from Skybrush Viewer."""

_ALLOWED_VIEWER_NETWORKS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
)
"""Networks a Skybrush Viewer URL may point to; the Viewer runs locally."""


def _effective_timeout() -> float:
    """Returns the per-request timeout, honoring a shorter socket default."""
    default_timeout = getdefaulttimeout()
    if default_timeout is None or default_timeout > _VIEWER_TIMEOUT:
        return _VIEWER_TIMEOUT
    return default_timeout


def _resolve_hostname(hostname: str, timeout: float = 2.0) -> list:
    """Resolves a hostname to IP addresses, giving up after `timeout` seconds.

    getaddrinfo() has no timeout of its own, so the lookup runs in a daemon
    thread; a stalled DNS server must not freeze the Blender UI thread.
    """
    addresses = []

    def _lookup():
        """Runs the lookup; a failed lookup is reported as no addresses."""
        try:
            addresses.extend(info[4][0] for info in getaddrinfo(hostname, None))
        except Exception:
            pass

    thread = threading.Thread(target=_lookup, daemon=True)
    thread.start()
    thread.join(timeout)
    return addresses


def _is_allowed_viewer_url(url: str) -> bool:
    """Returns whether the given URL may be a Skybrush Viewer address.

    Only plain HTTP URLs pointing to a loopback or private (RFC 1918) address
    are accepted, so a rogue discovery response cannot redirect requests to a
    public host or a cloud metadata endpoint.
    """
    parsed = urlparse(url)
    if parsed.scheme != "http" or not parsed.hostname:
        return False
    try:
        addresses = [ipaddress.ip_address(parsed.hostname)]
    except ValueError:
        try:
            addresses = [
                ipaddress.ip_address(address)
                for address in _resolve_hostname(parsed.hostname)
            ]
        except ValueError:
            return False
    return bool(addresses) and all(
        any(
            address.version == network.version and address in network
            for network in _ALLOWED_VIEWER_NETWORKS
        )
        for address in addresses
    )


def _load_json_with_deadline(response, deadline: float):
    """Reads and parses a JSON response, stopping at the given deadline.

    The per-operation socket timeout alone does not bound the total time: a
    response trickling in slowly could keep the read going indefinitely. This
    reads the body a single recv at a time and stops as soon as the deadline
    passes. The deadline is an absolute `time.monotonic()` value shared with
    the request setup, so connect, headers and body share one budget.
    """
    read = getattr(response, "read1", response.read)
    chunks = []
    while True:
        if monotonic() > deadline:
            raise SocketTimeoutError("timed out")
        chunk = read(8192)
        if not chunk:
            break
        chunks.append(chunk)
    return loads(b"".join(chunks))


class SkybrushViewerError(RuntimeError):
    """Error thrown when a request to Skybrush Viewer fails."""


class SkybrushViewerNotFoundError(SkybrushViewerError):
    """Error thrown when it seems that Skybrush Viewer is not running on the
    current machine.
    """

    pass


class _ViewerRedirectHandler(HTTPRedirectHandler):
    """Rejects Viewer redirects to non-local addresses."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Follows a redirect only when the new URL is a local Viewer address."""
        if not _is_allowed_viewer_url(newurl):
            raise SkybrushViewerError(
                "Skybrush Viewer redirected to a non-local address"
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open_viewer_request(request, deadline: float):
    """Opens a Viewer request, bounding connect and header reads by `deadline`.

    urlopen reads the response headers inside the call, so a slow Viewer could
    keep the caller waiting past the per-operation socket timeout by trickling
    header bytes. The open runs in a daemon thread that is abandoned on timeout.
    """
    timeout = max(0.0, deadline - monotonic())
    outcome = []

    def _open():
        """Opens the request in a daemon thread, capturing the outcome."""
        try:
            outcome.append(
                build_opener(_ViewerRedirectHandler()).open(request, timeout=timeout)
            )
        except BaseException as ex:
            outcome.append(ex)

    thread = threading.Thread(target=_open, daemon=True)
    thread.start()
    thread.join(timeout)
    if not outcome:
        raise SocketTimeoutError("timed out")
    if isinstance(outcome[0], BaseException):
        raise outcome[0]
    return outcome[0]


class SkybrushViewerBridge:
    """Object that is responsible for discovering a running Skybrush Viewer
    instance on the current machine and for posting data to it.
    """

    def __init__(self):
        """Constructor."""
        self._discovery = SSDPAppDiscovery("urn:collmot-com:service:skyc-validator:1")

    def _send_request(self, path: str, *args, **kwds) -> dict:
        """Sends a request to the running Skybrush Viewer instance and returns
        the parsed JSON response.

        Retries the request at most once if it can be assumed that the Skybrush
        Viewer might be running at a different port.

        Raises:
            SkybrushViewerError: in case of request errors, server errors or if
                the Skybrush Viewer instance is not running
        """
        force = False
        timed_out_url = None

        while True:
            # On retry, only drop the cached URL if it is still the one that
            # timed out; a newer validation may have cached a different URL
            # since, and a stale worker must not discard it.
            url = self._discovery.discover(
                force=force, expected_url=timed_out_url if force else None
            )
            if url is None:
                raise SkybrushViewerNotFoundError()

            if url.endswith("/"):
                url = url[:-1]
            if path.startswith("/"):
                path = path[1:]
            url_and_path = f"{url}/api/v1/{path}"

            if not _is_allowed_viewer_url(url_and_path):
                self._discovery.invalidate()
                raise SkybrushViewerError("Skybrush Viewer URL is not a local address")

            if timed_out_url is not None and url.rstrip("/") == timed_out_url:
                # rediscovery found the same URL that just timed out, so there
                # is no different Viewer to retry against
                raise SkybrushViewerError(
                    "Timed out while waiting for Skybrush Viewer to respond"
                )

            request = Request(url_and_path, *args, **kwds)
            timeout = _effective_timeout()
            # One deadline covers connect, headers and body; each stage gets
            # only the remaining budget.
            deadline = monotonic() + timeout

            try:
                with _open_viewer_request(request, deadline) as response:
                    result = _load_json_with_deadline(response, deadline)
                    if isinstance(result, dict):
                        return result
                    else:
                        raise SkybrushViewerError(
                            "Invalid response received from Skybrush Viewer"
                        )

            except SocketTimeoutError:
                if force:
                    raise SkybrushViewerError(
                        "Timed out while waiting for Skybrush Viewer to respond"
                    ) from None
                # the Viewer may have moved; retry once, but only against a
                # different URL (checked at the top of the loop)
                timed_out_url = url.rstrip("/")
                pass

            except HTTPError as err:
                # unrecoverable error; we invalidate the cached URL but we
                # don't try again
                self._discovery.invalidate(url)
                if err.code >= 500:
                    raise SkybrushViewerError(
                        "Skybrush Viewer indicated an unexpected error"
                    ) from None
                elif err.code == 404:
                    # Not found
                    self._discovery.invalidate(url)
                    raise SkybrushViewerNotFoundError() from None
                elif err.code == 400:
                    # Bad request
                    raise SkybrushViewerError(
                        "Skybrush Viewer indicated that the input format is invalid"
                    ) from None
                else:
                    raise

            except URLError as err:
                if isinstance(err.reason, SocketTimeoutError):
                    # urlopen wraps a socket timeout in URLError; treat it
                    # like a bare timeout so the rediscovery retry still applies
                    if force:
                        raise SkybrushViewerError(
                            "Timed out while waiting for Skybrush Viewer to respond"
                        ) from None
                    timed_out_url = url.rstrip("/")
                elif err.reason and getattr(err.reason, "errno", None) == ECONNREFUSED:
                    # try again
                    pass
                else:
                    # unrecoverable error; we invalidate the cached URL but we
                    # don't try again
                    self._discovery.invalidate(url)
                    raise

            except Exception:
                # unrecoverable error; we invalidate the cached URL but we
                # don't try again
                self._discovery.invalidate(url)
                raise

            if force:
                raise SkybrushViewerNotFoundError()
            else:
                # try again with a non-cached URL
                force = True

    def check_running(self) -> bool:
        """Returns whether the Skybrush Viewer instance is up and running."""
        result = self._send_request("ping")
        return bool(result.get("result"))

    def load_show_for_validation(
        self, show_data: bytes, *, filename: str | None = None
    ) -> None:
        """Asks the running Skybrush Viewer instance to load the given show data
        for validation.

        Parameters:
            show_data: the raw show data in .skyc format
            filename: name of the file that the data was generated from; used
                for data transfer to Skybrush Viewer
        """
        headers = {"Content-Type": "application/skybrush-compiled"}
        if filename:
            headers["X-Skybrush-Viewer-Title"] = filename[:512]

        result = self._send_request(
            "load",
            data=show_data,
            headers=headers,
        )

        if not result.get("result"):
            raise SkybrushViewerError("Invalid response received from Skybrush Viewer")


class SSDPAppDiscovery:
    """Object responsible for discovering the URL of a service based on its
    SSDP URN, and caching it for a limited amount of time.
    """

    def __init__(self, urn: str, *, max_age: float = 600):
        """Constructor.

        Parameters:
            urn: the SSDP URN of the service to discover
            max_age: the maximum number of seconds for which to discovered URL
                will be cached; defaults to 10 minutes
        """
        self._sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)
        self._sock.settimeout(1)

        self._urn = urn
        self._max_age = float(max_age)
        self._last_checked_at = 0
        self._url = None  # type: str | None
        self._lock = threading.RLock()

    def discover(
        self, force: bool = False, expected_url: str | None = None
    ) -> str | None:
        """Finds a running service instance on the current machine using SSDP
        and returns its URL.

        Parameters:
            force: whether to ensure that a fresh URL is fetched even if we
                have a cached one
            expected_url: when forcing a refresh, only drop the cached URL if
                it still matches this one, so a newer validation's discovery
                result is not discarded by a stale worker

        Returns:
            the URL of the running service instance or `None` if no service with
            the associated URN is running at the moment
        """
        if force:
            self.invalidate(expected_url)
        with self._lock:
            if (
                self._url is not None
                and monotonic() - self._last_checked_at <= self._max_age
            ):
                return self._url
        # The SSDP query runs without the lock so a slow network cannot block
        # another request's discovery.
        url = self._update_url()
        with self._lock:
            self._url = url
            self._last_checked_at = monotonic()
        return url

    def invalidate(self, url: str | None = None) -> None:
        """Invalidates the currently cached instance of the service URL.

        When `url` is given, the cache is cleared only if it still holds that
        URL, so a stale worker cannot discard a newer validation's discovery.
        """
        with self._lock:
            if url is None or self._url == url:
                self._last_checked_at = 0
                self._url = None

    def _update_url(self) -> str | None:
        """Updates the URL of the running service instance unconditionally."""
        message = (
            f"M-SEARCH * HTTP/1.1\r\n"
            f"HOST:239.255.255.250:1900\r\n"
            f"ST:{self._urn}\r\n"
            f"MX:2\r\n"
            f'MAN:"ssdp:discover"\r\n'
            f"\r\n"
        ).encode("ascii")

        # Apparently, sending a datagram to 127.0.0.1 does not work even if we
        # are only interested in Viewer instances running on the same machine
        try:
            self._sock.sendto(message, ("239.255.255.250", 1900))
        except OSError as ex:
            if ex.errno == ENETUNREACH:
                # This may happen if the user is not connected to any network
                # at all; in this case we retry with 127.0.0.1
                self._sock.sendto(message, ("127.0.0.1", 1900))

        # There may be pending SSDP responses in the queue so we read at most
        # 10 times, looking for messages where the date is not too old
        attempts = 10
        location = None
        while attempts > 0:
            attempts -= 1
            date_ok = False
            location = None

            try:
                # TODO(ntamas): reject packets that come from a different machine.
                # Unfortunately it's complicated; we would need something like
                # the 'netifaces' module to get all IP addresses reliably, and
                # it is not platform-independent
                data, addr = self._sock.recvfrom(65507)
            except SocketTimeoutError:
                return

            if not data.startswith(b"HTTP/1.1 200 OK\r\n"):
                continue

            lines = data.split(b"\r\n")
            for line in lines:
                key, _, value = line.partition(b":")
                key = key.decode("ascii", "replace").upper().strip()
                if key == "LOCATION":
                    location = value.decode("ascii", "replace").strip()
                elif key == "DATE":
                    try:
                        parsed_date = parsedate_to_datetime(
                            value.decode("ascii", "replace")
                        )
                    except ValueError:
                        continue

                    if (
                        parsed_date.tzinfo is None
                        or parsed_date.tzinfo.utcoffset(parsed_date) is None
                    ):
                        diff = parsed_date - datetime.now()
                    else:
                        diff = parsed_date - datetime.now(parsed_date.tzinfo)

                    if abs(diff.total_seconds()) < 5:
                        date_ok = True

            if location and date_ok:
                break

        return location
