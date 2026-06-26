from collections.abc import Iterator
from contextlib import contextmanager
from gzip import compress
from http import HTTPStatus
from http.client import HTTPResponse
from io import IOBase, TextIOWrapper
from json import dumps as json_dumps
from json import load as json_load
from json import loads as json_loads
from pathlib import Path
from shutil import copyfileobj
from ssl import CERT_NONE, create_default_context
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

from sbstudio.utils import create_path_and_open

from .errors import SkybrushStudioAPIError

__all__ = (
    "Response",
    "SkybrushStudioBaseAPI",
)


class Response:
    """Class representing a response from the Skybrush Studio/Gateway APIs."""

    def __init__(self, response: HTTPResponse):
        """Constructor.

        Parameters:
            response: the raw HTTP response that this object wraps
        """
        self._response = response

    @property
    def content_type(self) -> str:
        """Returns the HTTP content type of the response."""
        return self._response.headers.get_content_type()

    @property
    def status_code(self) -> int:
        """Returns the HTTP status code of the response."""
        return self._response.status

    def _run_sanity_checks(self) -> None:
        """Runs basic sanity checks on the wrapped HTTP response and raises
        appropriate exceptions when the HTTP response signals an error.
        """
        if self.status_code not in (200, 201):
            raise SkybrushStudioAPIError(
                f"Request returned HTTP error code {self.status_code}"
            )

        if self.content_type not in (
            "application/octet-stream",
            "application/json",
            "application/zip",
            "text/plain",
        ):
            raise SkybrushStudioAPIError(
                f"Unexpected content type {self.content_type!r} in response"
            )

    def as_bytes(self) -> bytes:
        """Reads the whole response body and returns it as a bytes object."""
        if self.content_type not in ("application/octet-stream", "application/zip"):
            raise SkybrushStudioAPIError("Response type is not an octet stream")
        return self._response.read()

    def as_file_object(self) -> IOBase:
        """Returns the response body as a file-like object."""
        return self._response

    def as_json(self):
        """Parses the response body as JSON and returns the parsed object."""
        if self.content_type != "application/json":
            raise SkybrushStudioAPIError("Response type is not JSON")
        return json_load(TextIOWrapper(self._response, encoding="utf-8"))

    def as_str(self) -> str:
        """Reads the whole response body and return it as a string."""
        if self.content_type not in (
            "application/octet-stream",
            "application/json",
            "application/zip",
            "text/plain",
        ):
            raise SkybrushStudioAPIError("Invalid response type")

        data = self._response.read()
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        return data

    def get_header(self, name: str) -> str | None:
        """Returns the value of the response header matching name."""
        return self._response.getheader(name)

    def save_to_file(self, filename: str | Path) -> None:
        """Writes response to a given file."""
        with create_path_and_open(filename, "wb") as f:
            copyfileobj(self._response, f)


_MISSING = object()
"""Special object to denote a missing `json` argument internally in
`SkybrushStudioBaseAPI._send_request()`. Used to distinguish the case of
"no `json` parameter provided" from the case of "user provided `None` as `json`".
"""


class SkybrushStudioBaseAPI:
    """Base class that represents a connection to the API of
    either Skybrush Studio Server or Skybrush Studio Gateway.
    """

    _api_key: str | None
    """The optional API key that will be submitted with each request."""

    _http_status: dict[int | None, str]
    """Predefined HTTP status messages."""

    _root: str
    """The root URL of the API, with a trailing slash."""

    def __init__(self, url: str):
        """Constructor.

        Parameters:
            url: the root URL of the Skybrush API
        """
        self._api_key = None
        self._request_context = create_default_context()
        self._http_status = {status.value: status.phrase for status in HTTPStatus}
        self._http_status[None] = "HTTP error"

        self.url = url

    def joined_url(self, url: str) -> str:
        """Returns a full normalized url from the API root and a relative url.

        Args:
            url: the URL relative to the API root."""

        url = urljoin(self.url, url.rstrip("/"))

        # replace localhost to 127.0.0.1 to force IPv4
        parsed = urlparse(url)
        if parsed.hostname == "localhost":
            parsed = parsed._replace(
                netloc=parsed.netloc.replace("localhost", "127.0.0.1")
            )
            return urlunparse(parsed)

        return url

    @property
    def url(self) -> str:
        """The URL where the API can be accessed."""
        return self._root

    @url.setter
    def url(self, value: str) -> None:
        if not value.endswith("/"):
            value += "/"
        self._root = value

    @contextmanager
    def _send_request(
        self,
        url: str,
        *,
        data: bytes | None = None,
        json: Any = _MISSING,
        allow_compression: bool = True,
        method: str | None = None,
    ) -> Iterator[Response]:
        """Sends a request to the given URL, relative to the API root, and
        returns the corresponding HTTP response object.

        The content type of the request is determined automatically from the presence
        of the `json` and `data` parameters. When `json` is present, the request body
        is assumed to be a JSON object with content type `application/json`. When
        `data` is present, the request body is assumed to be a raw bytes object with
        content type `application/octet-stream`. `json` and `data` must not be present
        at the same time.

        Parameters:
            url: the URL (relative to the API root) where the request should be
                sent to. The request will be a GET request when the data is
                omitted or `None`, otherwise it will be a POST request.
            data: the raw body of the request, as a `bytes` object. Mutually exclusive
                with `json`, i.e. if `json` is provided, `data` must not be provided.
            json: the body of the request as a JSON object. Mutually exclusive with
                `data`, i.e. if `data` is provided, `json` must not be provided.
            allow_compression: specifies whether the function is allowed to compress the
                request body when it makes sense. Set it to `False` to prevent the
                compression of the request body, which is useful if you already know
                that it is compressed. `True` means that the function is free to decide
                whether it will use compression or not. The current implementation does
                not compress small pieces of data (less than 4K).
            method: explicit HTTP rqeuest method to use, or `None` to infer
                automatically. `None` means to use GET if there is no request body
                and POST if there is a request body (either `data` or `json`), even
                if the body is empty (zero bytes).

        Raises:
            SkybrushStudioAPIError: when the request returned a non-successful
                HTTP error code or an invalid content type
            ValueError: for invalid parameters like providing `json` and `data` at the
                same time
        """
        content_type: str | None = None
        content_encoding: str | None = None

        if json is not _MISSING:
            if data is not None:
                raise ValueError("at most one of `json` or `data` must be provided")

            data = json_dumps(json).encode("utf-8")
            content_type = "application/json"
        elif data is not None:
            content_type = "application/octet-stream"

        if method is None:
            method = "POST" if data is not None else "GET"

        if allow_compression and data is not None and len(data) >= 4096:
            data = compress(data)
            content_encoding = "gzip"

        # We should attempt to produce a signature even if the request body is empty
        signature = self._sign_request_body(data or b"")

        headers = {}
        if content_type is not None:
            headers["Content-Type"] = content_type
        if content_encoding is not None:
            headers["Content-Encoding"] = content_encoding
        if self._api_key is not None:
            headers["X-Skybrush-API-Key"] = self._api_key
        if signature is not None:
            headers["X-Skybrush-Request-Signature"] = signature

        req = Request(self.joined_url(url), data=data, headers=headers, method=method)

        try:
            with urlopen(req, context=self._request_context) as raw_response:
                response = Response(raw_response)
                response._run_sanity_checks()
                yield response
        except HTTPError as ex:
            # If the status code is 400, 403 or 500, we may have more details about the
            # error in the response itself
            if ex.status in (400, 403, 500):
                try:
                    body = ex.read().decode("utf-8")
                except Exception:
                    # decoding failed, let's pretend that we don't have a
                    # response body
                    body = "{}"
                try:
                    decoded_body = json_loads(body)
                except Exception:
                    # response body is not valid JSON, let's pretend that we
                    # got an empty object
                    decoded_body = {}
                if isinstance(decoded_body, dict) and decoded_body.get("detail"):
                    detail = str(decoded_body.get("detail"))
                    raise SkybrushStudioAPIError(
                        f"{self._http_status[ex.status]}: {detail}"
                    ) from None
            elif ex.status == 413:
                # Content too large
                raise SkybrushStudioAPIError(
                    "You have reached the limits of the community server. "
                    "Consider purchasing a license for a local instance of "
                    "Skybrush Studio Server."
                ) from None

            # No detailed information about the error so use a generic message.
            # State that this is probably a server-side issue if the status code
            # does not start with 4 -- status codes between 400 and 499 are client-side
            # issues.
            raise SkybrushStudioAPIError(
                f"{self._http_status[ex.status]} ({ex.status})"
                + (
                    (
                        ". This is most likely a server-side issue; please contact us "
                        "and let us know."
                    )
                    if ex.status is None or ex.status < 400 or ex.status > 499
                    else ""
                )
            ) from ex

    def _sign_request_body(self, data: bytes) -> str | None:
        """Retrieves a signature for the given request body, which will be added to the
        request in the `X-Skybrush-Request-Signature` header.

        Returns:
            the signature to append or `None` if no signature is needed
        """
        return None

    def _skip_ssl_checks(self) -> None:
        """Configures the API object to skip SSL checks when making requests.
        This is a _very_ bad practice, but apparently there is some problem with
        the macOS version of Blender that prevents it from finding the system
        certificates, and there are reports that the same problem also applies
        to Linux, hence we provide this method for sake of convenience.
        """
        ctx = create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = CERT_NONE
        self._request_context = ctx
