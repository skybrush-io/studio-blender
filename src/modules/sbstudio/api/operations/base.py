import logging

from abc import ABCMeta, abstractmethod
from gzip import compress
from json import JSONEncoder
from pathlib import Path
from ssl import create_default_context, CERT_NONE
from typing import Union
from urllib.request import urlopen, Request

from ..enums import SkybrushJSONFormat

from sbstudio.api.base import Response
from sbstudio.utils import create_path_and_open


#############################################################################
# configure logger

log = logging.getLogger(__name__)


class SkybrushAPIOperationBase(metaclass=ABCMeta):
    """Meta class for Skybrush operations that animation software plugins
    shall use together with Skybrush Studio installed locally or
    through the online Skybrush Studio Server.

    """

    @abstractmethod
    def as_dict(self, format: SkybrushJSONFormat, ndigits: int = 3) -> dict:
        """Create a Skybrush-compatible dictionary representation of self.

        Parameters:
            format: the format of the output
            ndigits: round floats to this precision

        Return:
            dictionary representation of self
        """
        ...

    def as_json(self, format: SkybrushJSONFormat, ndigits: int = 3) -> str:
        """Create a Skybrush-compatible JSON representation of self.

        Parameters:
            format: the format of the JSON output
            ndigits: number of digits for floats in the JSON output

        Return:
            JSON string representation of self
        """
        if format == SkybrushJSONFormat.RAW:
            encoder = JSONEncoder(indent=2)
        elif format == SkybrushJSONFormat.ONLINE:
            encoder = JSONEncoder(separators=(",", ":"))
        else:
            raise NotImplementedError("Unknown Skybrush JSON format")

        return encoder.encode(self.as_dict(format=format, ndigits=ndigits))

    def save_to_json(
        self,
        output: Path,
        format: SkybrushJSONFormat,
        ndigits: int = 3,
    ) -> None:
        """Write a Skybrush-compatible JSON representation of the drone show
        stored in self to the given output file.

        Parameters:
            output: the file where the JSON content should be written
            format: the format of the JSON output
            ndigits: number of digits for floats in the JSON output

        """
        with create_path_and_open(output, "w") as f:
            f.write(self.as_json(format=format, ndigits=ndigits))

    def _ask_skybrush_studio_server(
        self, operation: str, output: Path = None
    ) -> Union[str, None]:
        """Call Skybrush Studio Server at https://studio.skybrush.io to
        perform the required operation on self.

        Parameters:
            operation: the name of the operation to perform
            output: the output path where results should be written

        Return:
            the server's response if output is None, None otherwise.
        """

        # create compressed message content
        data = compress(self.as_json(format=SkybrushJSONFormat.ONLINE).encode("utf-8"))
        headers = {
            "Content-Type": "application/json",
            "Content-Encoding": "gzip",
            "Accept": "application/octet-stream",
        }
        # create unverified SSL context; needed for macOS
        ctx = create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = CERT_NONE
        # create request
        url = fr"https://studio.skybrush.io/api/v1/operations/{operation}"
        req = Request(url, data=data, headers=headers, method="POST")
        # send it and wait for response
        log.info(
            f"sending http POST request to studio.skybrush.io, body size: {len(data)} bytes"
        )
        with urlopen(req, context=ctx) as raw_response:
            response = Response(raw_response)
            # check response for errors
            response._run_sanity_checks()
            # return response as a string
            if output is None:
                log.info("response received, returning as a string")
                return response.as_str()
            # or write it to a file
            else:
                log.info("response received, writing to file")
                response.save_to_file(output)
