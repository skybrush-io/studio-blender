from typing import Any
from .base import SkybrushStudioBaseAPI

__all__ = ("SkybrushSignerAPI",)


class SkybrushSignerAPI(SkybrushStudioBaseAPI):
    """Class that represents a connection to the API of a
    Skybrush Request Signer.
    """

    def get_hardware_id(self) -> str:
        """Gets the hardware ID of the current machine from the request signer."""
        with self._send_request("hwid") as response:
            result = response.as_str()

        return result

    def sign_request(self, data: dict[str, Any]) -> str:
        """Signs a JSON request issued by Skybrush Studio.

        Args:
            data: the JSON data to sign.

        Returns:
            the signed data to be sent to Skybrush Studio Server
        """
        with self._send_request("sign", data=data) as response:
            result = response.as_str()

        return result
