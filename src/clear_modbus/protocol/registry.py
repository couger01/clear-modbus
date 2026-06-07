"""Custom Modbus function-code registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clear_modbus.protocol.pdu import RequestPDU, ResponsePDU

__all__ = [
    "CustomFunctionCodeRegistry",
    "RequestDecoder",
    "ResponseDecoder",
    "default_function_code_registry",
]

RequestDecoder = Callable[[bytes], "RequestPDU"]
"""Callable that decodes custom request PDU payload bytes.

Parameters
----------
bytes
    Request PDU payload bytes after the function-code byte.

Returns
-------
RequestPDU
    Decoded request object.

"""

ResponseDecoder = Callable[[bytes, "RequestPDU"], "ResponsePDU"]
"""Callable that decodes custom response PDU payload bytes.

Parameters
----------
bytes
    Response PDU payload bytes after the function-code byte.
RequestPDU
    Original request object used as response-decoding context.

Returns
-------
ResponsePDU
    Decoded response object.

"""


@dataclass
class CustomFunctionCodeRegistry:
    """Registry for custom Modbus function-code decoders.

    Parameters
    ----------
    request_decoders : dict[int, RequestDecoder]
        Mapping from function code to request decoder.
    response_decoders : dict[int, ResponseDecoder]
        Mapping from function code to response decoder.

    Attributes
    ----------
    request_decoders : dict[int, RequestDecoder]
        Registered custom request decoders.
    response_decoders : dict[int, ResponseDecoder]
        Registered custom response decoders.

    """

    request_decoders: dict[int, RequestDecoder] = field(default_factory=dict)
    response_decoders: dict[int, ResponseDecoder] = field(default_factory=dict)

    def register_request_decoder(
        self, function_code: int, decoder: RequestDecoder
    ) -> None:
        """Register a custom request decoder.

        Parameters
        ----------
        function_code : int
            Custom function code from ``0x00`` through ``0x7F``.
        decoder : RequestDecoder
            Callable used to decode request payload bytes for ``function_code``.

        Raises
        ------
        ValueError
            If ``function_code`` is outside ``0x00`` through ``0x7F`` or a
            request decoder is already registered for the function code.

        """
        if not 0 <= function_code <= 0x7F:
            raise ValueError("function_code must be between 0x00 and 0x7F.")
        if function_code in self.request_decoders:
            raise ValueError(
                f"Request decoder already registered for 0x{function_code:02X}"
            )
        self.request_decoders[function_code] = decoder

    def register_response_decoder(
        self, function_code: int, decoder: ResponseDecoder
    ) -> None:
        """Register a custom response decoder.

        Parameters
        ----------
        function_code : int
            Custom function code from ``0x00`` through ``0x7F``.
        decoder : ResponseDecoder
            Callable used to decode response payload bytes for ``function_code``.

        Raises
        ------
        ValueError
            If ``function_code`` is outside ``0x00`` through ``0x7F`` or a
            response decoder is already registered for the function code.

        """
        if not 0 <= function_code <= 0x7F:
            raise ValueError("function_code must be between 0x00 and 0x7F.")
        if function_code in self.response_decoders:
            raise ValueError(
                f"Response decoder already registered for 0x{function_code:02X}"
            )
        self.response_decoders[function_code] = decoder

    def decode_request(self, function_code: int, payload: bytes) -> RequestPDU | None:
        """Decode a custom request PDU payload.

        Parameters
        ----------
        function_code : int
            Function code to look up.
        payload : bytes
            Request PDU payload bytes after the function-code byte.

        Returns
        -------
        RequestPDU | None
            Decoded request object, or ``None`` when no decoder is registered.

        """
        decoder = self.request_decoders.get(function_code)
        if decoder is None:
            return None
        return decoder(payload)

    def decode_response(
        self, function_code: int, payload: bytes, request: RequestPDU
    ) -> ResponsePDU | None:
        """Decode a custom response PDU payload.

        Parameters
        ----------
        function_code : int
            Function code to look up.
        payload : bytes
            Response PDU payload bytes after the function-code byte.
        request : RequestPDU
            Original request object used as response-decoding context.

        Returns
        -------
        ResponsePDU | None
            Decoded response object, or ``None`` when no decoder is registered.

        """
        decoder = self.response_decoders.get(function_code)
        if decoder is None:
            return None
        return decoder(payload, request)


default_function_code_registry = CustomFunctionCodeRegistry()
