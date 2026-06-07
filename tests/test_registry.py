from dataclasses import dataclass
from typing import ClassVar

import pytest

from clear_modbus import CustomFunctionCodeRegistry


@dataclass(frozen=True)
class CustomRegistryRequest:
    value: int

    function_code: ClassVar[int] = 0x41

    def encode(self) -> bytes:
        return bytes([self.function_code, self.value])


@dataclass(frozen=True)
class CustomRegistryResponse:
    value: int
    request_value: int

    function_code: ClassVar[int] = 0x41

    def encode(self) -> bytes:
        return bytes([self.function_code, self.value])


def test_registry_initializes_empty_decoder_mappings() -> None:
    registry = CustomFunctionCodeRegistry()

    assert registry.request_decoders == {}
    assert registry.response_decoders == {}


def test_registry_registers_and_decodes_request() -> None:
    registry = CustomFunctionCodeRegistry()
    registry.register_request_decoder(
        0x41,
        lambda payload: CustomRegistryRequest(value=payload[0]),
    )

    request = registry.decode_request(
        function_code=0x41,
        payload=bytes.fromhex("7B"),
    )

    assert request == CustomRegistryRequest(value=123)


def test_registry_registers_and_decodes_response_with_request_context() -> None:
    registry = CustomFunctionCodeRegistry()
    request = CustomRegistryRequest(value=10)

    def decode_custom_response(
        payload: bytes,
        request_pdu,
    ) -> CustomRegistryResponse:
        assert isinstance(request_pdu, CustomRegistryRequest)
        return CustomRegistryResponse(
            value=payload[0],
            request_value=request_pdu.value,
        )

    registry.register_response_decoder(0x41, decode_custom_response)

    response = registry.decode_response(
        function_code=0x41,
        payload=bytes.fromhex("14"),
        request=request,
    )

    assert response == CustomRegistryResponse(value=20, request_value=10)


def test_registry_returns_none_for_unregistered_request_decoder() -> None:
    registry = CustomFunctionCodeRegistry()

    assert registry.decode_request(function_code=0x41, payload=b"") is None


def test_registry_returns_none_for_unregistered_response_decoder() -> None:
    registry = CustomFunctionCodeRegistry()

    assert (
        registry.decode_response(
            function_code=0x41,
            payload=b"",
            request=CustomRegistryRequest(value=10),
        )
        is None
    )


@pytest.mark.parametrize("function_code", [-1, 0x80])
def test_registry_rejects_invalid_request_function_codes(function_code: int) -> None:
    registry = CustomFunctionCodeRegistry()

    with pytest.raises(ValueError):
        registry.register_request_decoder(
            function_code,
            lambda payload: CustomRegistryRequest(value=payload[0]),
        )


@pytest.mark.parametrize("function_code", [-1, 0x80])
def test_registry_rejects_invalid_response_function_codes(function_code: int) -> None:
    registry = CustomFunctionCodeRegistry()

    with pytest.raises(ValueError):
        registry.register_response_decoder(
            function_code,
            lambda payload, request: CustomRegistryResponse(
                value=payload[0],
                request_value=0,
            ),
        )


def test_registry_rejects_duplicate_request_decoders() -> None:
    registry = CustomFunctionCodeRegistry()
    registry.register_request_decoder(
        0x41,
        lambda payload: CustomRegistryRequest(value=payload[0]),
    )

    with pytest.raises(ValueError):
        registry.register_request_decoder(
            0x41,
            lambda payload: CustomRegistryRequest(value=payload[0]),
        )


def test_registry_rejects_duplicate_response_decoders() -> None:
    registry = CustomFunctionCodeRegistry()
    registry.register_response_decoder(
        0x41,
        lambda payload, request: CustomRegistryResponse(
            value=payload[0],
            request_value=0,
        ),
    )

    with pytest.raises(ValueError):
        registry.register_response_decoder(
            0x41,
            lambda payload, request: CustomRegistryResponse(
                value=payload[0],
                request_value=0,
            ),
        )
