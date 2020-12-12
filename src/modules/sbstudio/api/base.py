import json

from contextlib import contextmanager
from gzip import compress
from http.client import HTTPResponse
from io import IOBase, TextIOWrapper
from typing import Any, ContextManager, List, Optional, Sequence
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from sbstudio.model.types import Coordinate3D

from .errors import SkybrushStudioAPIError

__all__ = ("SkybrushStudioAPI",)


class Response:
    """Class representing a response from the Skybrush Studio API."""

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

        if self.content_type not in ("application/octet-stream", "application/json"):
            raise SkybrushStudioAPIError(
                f"Unexpected content type {self.content_type!r} in response"
            )

    def as_bytes(self) -> bytes:
        """Reads the whole response body and returns it as a bytes object."""
        if self.content_type != "application/octet-stream":
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


class SkybrushStudioAPI:
    """Class that represents a connection to the API of a Skybrush Studio
    server.
    """

    def __init__(self, url: str = "https://studio.skybrush.io/api/v1/"):
        """Constructor.

        Parameters:
            url: the root URL of the Skybrush Studio API; defaults to the public
                online service
        """
        if not url.endswith("/"):
            url += "/"
        self._root = url

    @contextmanager
    def _send_request(self, url: str, data: Any = None) -> ContextManager[Response]:
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

        Raises:
            SkybrushStudioAPIError: when the request returned a non-successful
                HTTP error code or an invalid content type
        """
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

        headers = {"Content-Type": content_type}
        if content_encoding is not None:
            headers["Content-Encoding"] = content_encoding

        url = urljoin(self._root, url.lstrip("/"))
        req = Request(url, data=data, headers=headers, method=method)
        with urlopen(req) as raw_response:
            response = Response(raw_response)
            response._run_sanity_checks()
            yield response

    def match_points(
        self, source: Sequence[Coordinate3D], target: Sequence[Coordinate3D]
    ) -> List[Optional[int]]:
        """Matches the points of a source point set to the points of a
        target point set in a way that ensures collision-free straight-line
        trajectories between the matched points when neither the source nor the
        target points are too close to each other.
        """
        data = {"version": 1, "source": source, "target": target}
        with self._send_request("operations/match-points", data) as response:
            result = response.as_json()

        if result.get("version") != 1:
            raise SkybrushStudioAPIError("invalid response version")

        return result.get("mapping")


def test():
    api = SkybrushStudioAPI()
    print(
        repr(
            api.match_points(
                [[0, 0, 0], [1, 0, 0], [-1, 0, 0]],
                [[0, 0, 10], [0, 1, 10], [0, -1, 10]],
            )
        )
    )


if __name__ == "__main__":
    test()
