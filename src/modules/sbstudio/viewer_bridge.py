"""Classes related to discovering a running Skybrush Viewer instance on the
current machine and for posting data to it.
"""

from datetime import datetime
from email.utils import parsedate_to_datetime
from errno import ECONNREFUSED
from json import load
from socket import (
    socket,
    timeout as SocketTimeoutError,
    AF_INET,
    SOCK_DGRAM,
    IPPROTO_UDP,
)
from time import monotonic
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

__all__ = ("SkybrushViewerBridge",)


class SkybrushViewerError(RuntimeError):
    pass


class SkybrushViewerNotFoundError(SkybrushViewerError):
    """Error thrown when it seems that Skybrush Viewer is not running on the
    current machine.
    """

    pass


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

        while True:
            url = self._discovery.discover(force=force)
            if url is None:
                raise SkybrushViewerNotFoundError()

            if url.endswith("/"):
                url = url[:-1]
            if path.startswith("/"):
                path = path[1:]
            url_and_path = f"{url}/api/v1/{path}"

            request = Request(url_and_path, *args, **kwds)

            try:
                with urlopen(request) as response:
                    result = load(response)
                    print("Got", repr(result))
                    if isinstance(result, dict):
                        return result
                    else:
                        raise SkybrushViewerError(
                            "Invalid response received from Skybrush Viewer"
                        )

            except HTTPError as err:
                # unrecoverable error; we invalidate the cached URL but we
                # don't try again
                self._discovery.invalidate()
                if err.code >= 500:
                    raise SkybrushViewerError(
                        "Skybrush Viewer indicated an unexpected error"
                    )
                elif err.code == 404:
                    # Not found
                    self._discovery.invalidate()
                    raise SkybrushViewerNotFoundError()
                elif err.code == 400:
                    # Bad request
                    raise SkybrushViewerError(
                        "Skybrush Viewer indicated that the input format is invalid"
                    )
                else:
                    raise

            except URLError as err:
                if err.reason and getattr(err.reason, "errno", None) == ECONNREFUSED:
                    # try again
                    pass
                else:
                    # unrecoverable error; we invalidate the cached URL but we
                    # don't try again
                    self._discovery.invalidate()
                    raise

            except Exception:
                # unrecoverable error; we invalidate the cached URL but we
                # don't try again
                self._discovery.invalidate()
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

    def load_show_for_validation(self, show_data: bytes) -> None:
        """Asks the running Skybrush Viewer instance to load the given show data
        for validation.
        """
        result = self._send_request(
            "load",
            data=show_data,
            headers={"Content-Type": "application/skybrush-compiled"},
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
        self._url = None  # type: Optional[str]

    def discover(self, force: bool = False) -> Optional[str]:
        """Finds a running service instance on the current machine using SSDP
        and returns its URL.

        Parameters:
            force: whether to ensure that a fresh URL is fetched even if we
                have a cached one

        Returns:
            the URL of the running service instance or `None` if no service with
            the associated URN is running at the moment
        """
        if force:
            self.invalidate()
        self._update_url_if_needed()
        print("Returning URL:", self._url)
        return self._url

    def invalidate(self) -> None:
        """Invalidates the currently cached instance of the service URL."""
        self._last_checked_at = 0
        self._url = None

    def _update_url_if_needed(self) -> None:
        """Updates the URL of the running service instance on the current
        machine using SSDP if needed.
        """
        now = monotonic()
        if self._url is None or now - self._last_checked_at > self._max_age:
            self._url = self._update_url()
            self._last_checked_at = monotonic()

    def _update_url(self) -> Optional[str]:
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
        self._sock.sendto(message, ("239.255.255.250", 1900))

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
