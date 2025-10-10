import json

from collections.abc import Iterator
from contextlib import contextmanager
from gzip import compress
from http import HTTPStatus
from http.client import HTTPResponse
from io import IOBase, TextIOWrapper
from pathlib import Path
from shutil import copyfileobj
from ssl import create_default_context, CERT_NONE
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from sbstudio.utils import create_path_and_open

from .errors import SkybrushStudioAPIError

__all__ = (
    "SkybrushStudioResponse",
    "SkybrushStudioBaseAPI",
)


class SkybrushStudioResponse:
    """Class representing a response from the Skybrush Studio/Signer APIs."""

    def __init__(self, response: HTTPResponse):
        """Constructor.

        Parameters:
            response: the raw HTTP response that this object wraps
        """
        self._response = response

    @property
    def content_type(self) -> str:
        """Returns the HTTP content type of the response."""
        info = self._response.info()
        return info.get_content_type()

    def _run_sanity_checks(self) -> None:
        """Runs basic sanity checks on the wrapped HTTP response and raises
        appropriate exceptions when the HTTP response signals an error.
        """
        status_code = self._response.getcode()
        if status_code != 200:
            raise SkybrushStudioAPIError(
                f"Request returned HTTP error code {status_code}"
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
        return json.load(TextIOWrapper(self._response, encoding="utf-8"))

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

    def save_to_file(self, filename: Path) -> None:
        """Writes response to a given file."""
        with create_path_and_open(filename, "wb") as f:
            copyfileobj(self._response, f)


class SkybrushStudioBaseAPI:
    """Base class that represents a connection to the API of
    either Skybrush Studio Server or Skybrush Request Signer.
    """

    _root: str
    """The root URL of the API, with a trailing slash"""

    _http_status: dict[int | None, str]
    """Predefined HTTP status messages."""

    def __init__(self, url: str):
        """Constructor.

        Parameters:
            url: the root URL of the Skybrush API
        """
        self._api_key = None
        self._root = None  # type: ignore
        self._request_context = create_default_context()
        self._http_status = {status.value: status.phrase for status in HTTPStatus}
        self._http_status[None] = "HTTP error"

        self.url = url

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
        self, url: str, data: Any = None, *, signature: str | None = None
    ) -> Iterator[SkybrushStudioResponse]:
        """Sends a request to the given URL, relative to the API root, and
        returns the corresponding HTTP response object.

        Parameters:
            url: the URL (relative to the API root) where the request should be
                sent to. The request will be a GET request when the data is
                omitted or `None`, otherwise it will be a POST request.
            data: the body of the request; must be an arbitrary Python object
                that can be encoded as JSON, or a `bytes` object. The content type
                of the request will be determined based on the type of this
                parameter; when `data` is a `bytes` object, it is sent as the
                request body directly and the content type will be
                `application/octet-stream`. When `data` is any other Python
                object, it will be encoded as JSON, compressed with `gzip` and
                then sent as a request with `Content-Type` equal to
                `application/json`.
            signature: an optional digital signature of the request for
                server side validation

        Raises:
            SkybrushStudioAPIError: when the request returned a non-successful
                HTTP error code or an invalid content type
        """
        content_type = None
        content_encoding = None

        if data is None:
            method = "GET"
        else:
            method = "POST"
            if not isinstance(data, bytes):
                data = json.dumps(data).encode("utf-8")
                content_type = "application/json"
                content_encoding = "gzip"
            else:
                content_type = "application/octet-stream"

        if content_encoding == "gzip":
            data = compress(data)

        headers = {}
        if content_type is not None:
            headers["Content-Type"] = content_type
        if content_encoding is not None:
            headers["Content-Encoding"] = content_encoding
        if self._api_key is not None:
            headers["X-Skybrush-API-Key"] = self._api_key
        if signature is not None:
            headers["X-Skybrush-Request-Signature"] = signature

        url = urljoin(self._root, url.lstrip("/"))
        req = Request(url, data=data, headers=headers, method=method)

        try:
            with urlopen(req, context=self._request_context) as raw_response:
                response = SkybrushStudioResponse(raw_response)
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
                    decoded_body = json.loads(body)
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

            # No detailed information about the error so use a generic message
            raise SkybrushStudioAPIError(
                f"{self._http_status[ex.status]} ({ex.status}). "
                f"This is most likely a server-side issue; please contact us and let us know."
            ) from ex

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
