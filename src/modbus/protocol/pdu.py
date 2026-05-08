from dataclasses import dataclass
from typing import ClassVar, Protocol

MAX_READ_REGISTERS = 125
MAX_WRITE_REGISTERS = 123
MAX_REGISTER_VALUE = 0xFFFF


def validate_register_address(address: int) -> None:
    if not 0 <= address <= MAX_REGISTER_VALUE:
        raise ValueError("address is not between 0 and 0xFFFF.")


def validate_register_count(count: int, max_count: int = MAX_READ_REGISTERS) -> None:
    if not 1 <= count <= max_count:
        raise ValueError("count is not between 1 and max_count.")


def validate_register_value(value: int) -> None:
    if not 0 <= value <= MAX_REGISTER_VALUE:
        raise ValueError("value is not between 0 and 0xFFFF.")


class RequestPDU(Protocol):
    @property
    def function_code(self) -> int: ...

    def encode(self) -> bytes: ...


class ResponsePDU(Protocol):
    @property
    def function_code(self) -> int: ...

    def encode(self) -> bytes: ...


@dataclass(frozen=True)
class ReadHoldingRegistersRequest:
    address: int
    count: int

    function_code: ClassVar[int] = 0x03

    def encode(self) -> bytes:
        return (
            bytes([self.function_code])
            + self.address.to_bytes(2, "big")
            + self.count.to_bytes(2, "big")
        )

    def __post_init__(self) -> None:
        validate_register_address(self.address)
        validate_register_count(self.count)


@dataclass(frozen=True)
class ReadInputRegistersRequest:
    address: int
    count: int

    function_code: ClassVar[int] = 0x04

    def encode(self) -> bytes:
        payload = bytearray()
        payload.append(self.function_code)
        payload += self.address.to_bytes(2, "big")
        payload += self.count.to_bytes(2, "big")
        return bytes(payload)

    def __post_init__(self) -> None:
        validate_register_address(self.address)
        validate_register_count(self.count)


@dataclass(frozen=True)
class ReadRegistersResponse:
    function_code: int
    values: list[int]

    def encode(self) -> bytes:
        payload = bytearray()
        payload.append(self.function_code)
        payload.append(len(self.values) * 2)

        for value in self.values:
            payload += value.to_bytes(2, "big")

        return bytes(payload)

    @classmethod
    def decode(cls, function_code: int, payload: bytes) -> "ReadRegistersResponse":
        if len(payload) == 0:
            raise ValueError("Length of payload is 0.")

        byte_count = payload[0]
        register_bytes = payload[1:]

        if byte_count != len(register_bytes):
            raise ValueError("Register byte count does not match payload length")
        if byte_count % 2 != 0:
            raise ValueError("Register byte count must be even")
        values = [
            int.from_bytes(register_bytes[i : i + 2], "big")
            for i in range(0, len(register_bytes), 2)
        ]

        return cls(function_code=function_code, values=values)


@dataclass(frozen=True)
class WriteSingleRegisterRequest:
    address: int
    value: int

    function_code: ClassVar[int] = 0x06

    def encode(self) -> bytes:
        return (
            bytes([self.function_code])
            + self.address.to_bytes(2, "big")
            + self.value.to_bytes(2, "big")
        )

    def __post_init__(self) -> None:
        validate_register_address(self.address)
        validate_register_value(self.value)


@dataclass(frozen=True)
class WriteSingleRegisterResponse:
    function_code: int
    address: int
    value: int

    def encode(self) -> bytes:
        return bytes([self.function_code]) + self.address.to_bytes(2, "big") + self.value.to_bytes(2, "big")

    @classmethod
    def decode(cls, payload: bytes) -> "WriteSingleRegisterResponse":
        # function code: Write Single Register
        # 00 05 address
        # 00 7B value
        if len(payload) != 4:
            raise ValueError()

        address = int.from_bytes(payload[0:2], "big")
        value = int.from_bytes(payload[2:4], "big")

        return cls(function_code=0x06, address=address, value=value)


@dataclass(frozen=True)
class WriteMultipleRegistersRequest:
    address: int
    values: list[int]

    function_code: ClassVar[int] = 0x10

    def encode(self) -> bytes:
        byte_count = len(self.values) * 2
        payload = bytearray()
        payload.append(self.function_code)
        payload += self.address.to_bytes(2, "big")
        payload += len(self.values).to_bytes(2, "big")
        payload.append(byte_count)
        for value in self.values:
            payload += value.to_bytes(2, "big")
        return bytes(payload)

    def __post_init__(self) -> None:
        validate_register_address(self.address)
        validate_register_count(len(self.values), MAX_WRITE_REGISTERS)
        for value in self.values:
            validate_register_value(value)


@dataclass(frozen=True)
class WriteMultipleRegistersResponse:
    function_code: int
    address: int
    count: int

    def encode(self) -> bytes:
        return (bytes([self.function_code]) + self.address.to_bytes(2, "big") + self.count.to_bytes(2, "big"))

    @classmethod
    def decode(cls, payload: bytes) -> "WriteMultipleRegistersResponse":
        if len(payload) != 4:
            raise ValueError()
        address = int.from_bytes(payload[0:2], "big")
        count = int.from_bytes(payload[2:4], "big")
        return cls(function_code=0x10, address=address, count=count)


@dataclass(frozen=True)
class ExceptionResponse:
    function_code: int
    exception_code: int

    def encode(self) -> bytes:
        return bytes([self.function_code | 0x80, self.exception_code])

    @classmethod
    def decode(cls, function_code: int, payload: bytes) -> "ExceptionResponse":
        if len(payload) != 1:
            raise ValueError()
        exception_code = payload[0]
        return cls(function_code & 0x7F, exception_code=exception_code)


def decode_response_pdu(data: bytes, request: RequestPDU) -> ResponsePDU:
    if len(data) == 0:
        raise ValueError()
    function_code = data[0]
    payload = data[1:]

    if function_code & 0x80:
        exception_function_code = function_code & 0x7F
        if exception_function_code != request.function_code:
            raise ValueError()
        return ExceptionResponse.decode(function_code, payload)

    if function_code != request.function_code:
        raise ValueError()

    if function_code in (0x03, 0x04):
        return ReadRegistersResponse.decode(function_code, payload)
    if function_code == 0x06:
        return WriteSingleRegisterResponse.decode(payload)
    if function_code == 0x10:
        return WriteMultipleRegistersResponse.decode(payload)
    else:
        raise ValueError()
        
