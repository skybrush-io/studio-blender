from typing import Any
from .base import SkybrushStudioBaseAPI

__all__ = ("SkybrushGatewayAPI",)


class SkybrushGatewayAPI(SkybrushStudioBaseAPI):
    """Class that represents a connection to the API of a
    Skybrush Gateway for request signing and progress display.
    """

    def get_hardware_id(self) -> str:
        """Gets the hardware ID of the current machine from the Studio Gateway."""
        with self._send_request("hwid") as response:
            result = response.as_str()

        return result

    def sign_request(self, data: Any, *, compressed: bool = False) -> str:
        """Signs a JSON request issued by Skybrush Studio.

        Args:
            data: the raw or compressed data to sign
            compressed: whether data is an already gzip-compressed JSON-object

        Returns:
            the signed data to be sent to Skybrush Studio Server
        """
        with self._send_request(
            "sign", data=data, compressed=compressed, enforce_post=True
        ) as response:
            result = response.as_str()

        return result
