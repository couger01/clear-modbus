"""Protocol Data Unit types and decoders for supported Modbus functions."""

from dataclasses import dataclass
from enum import IntEnum
from struct import pack, unpack, unpack_from
from typing import ClassVar, Protocol

from clear_modbus.exceptions import ModbusPDUError
from clear_modbus.protocol.functions import FunctionCode
from clear_modbus.protocol.registry import default_function_code_registry

MAX_READ_REGISTERS = 125
MAX_WRITE_REGISTERS = 123
MAX_READ_WRITE_REGISTERS_WRITE = 121
MAX_REGISTER_VALUE = 0xFFFF
MAX_READ_BITS = 2000
MAX_WRITE_BITS = 1968
READ_DEVICE_IDENTIFICATION_MEI_TYPE = 0x0E
MAX_DEVICE_IDENTIFICATION_OBJECT_LENGTH = 244
COIL_ON = 0xFF00
COIL_OFF = 0x0000
_BITS_MASKS = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80)
_UNPACKED_BITS_BY_BYTE = tuple(
    tuple(bool(byte & mask) for mask in _BITS_MASKS) for byte in range(256)
)

__all__ = [
    "ExceptionResponse",
    "DeviceIdentificationObject",
    "DeviceIdentificationReadCode",
    "DeviceIdentificationConformityLevel",
    "ReadBitsResponse",
    "ReadCoilsRequest",
    "ReadDeviceIdentificationRequest",
    "ReadDeviceIdentificationResponse",
    "ReadDiscreteInputsRequest",
    "ReadHoldingRegistersRequest",
    "ReadInputRegistersRequest",
    "ReadRegistersResponse",
    "ReadWriteMultipleRegistersRequest",
    "RequestPDU",
    "ResponsePDU",
    "MaskWriteRegisterRequest",
    "MaskWriteRegisterResponse",
    "WriteMultipleCoilsRequest",
    "WriteMultipleCoilsResponse",
    "WriteMultipleRegistersRequest",
    "WriteMultipleRegistersResponse",
    "WriteSingleCoilRequest",
    "WriteSingleCoilResponse",
    "WriteSingleRegisterRequest",
    "WriteSingleRegisterResponse",
    "decode_request_pdu",
    "decode_response_pdu",
    "pack_bits",
    "unpack_bits",
    "validate_bit_count",
    "validate_device_identification_object_id",
    "validate_device_identification_object_value",
    "validate_register_address",
    "validate_register_count",
    "validate_register_value",
]


def validate_register_address(address: int) -> None:
    """Validate a Modbus address.

    Parameters
    ----------
    address : int
        Address to validate.

    Raises
    ------
    ValueError
        If ``address`` is outside ``0`` through ``0xFFFF``.

    """
    if not 0 <= address <= MAX_REGISTER_VALUE:
        raise ValueError("address is not between 0 and 0xFFFF.")


def validate_register_count(count: int, max_count: int = MAX_READ_REGISTERS) -> None:
    """Validate a register quantity.

    Parameters
    ----------
    count : int
        Register count to validate.
    max_count : int, optional
        Maximum accepted count.

    Raises
    ------
    ValueError
        If ``count`` is not between ``1`` and ``max_count``.

    """
    if not 1 <= count <= max_count:
        raise ValueError("count is not between 1 and max_count.")


def validate_register_value(value: int) -> None:
    """Validate a 16-bit register value.

    Parameters
    ----------
    value : int
        Register value to validate.

    Raises
    ------
    ValueError
        If ``value`` is outside ``0`` through ``0xFFFF``.

    """
    if not 0 <= value <= MAX_REGISTER_VALUE:
        raise ValueError("value is not between 0 and 0xFFFF.")


def validate_bit_count(count: int, max_count: int = MAX_READ_BITS) -> None:
    """Validate a coil or discrete-input quantity.

    Parameters
    ----------
    count : int
        Bit count to validate.
    max_count : int, optional
        Maximum accepted count.

    Raises
    ------
    ValueError
        If ``count`` is not between ``1`` and ``max_count``.

    """
    if not 1 <= count <= max_count:
        raise ValueError("count is not between 1 and max_count.")


def validate_device_identification_object_id(object_id: int) -> None:
    """Validate a read-device-identification object identifier.

    Raises
    ------
    ValueError
        If ``object_id`` is outside ``0`` through ``0xFF``.

    """
    if not 0 <= object_id <= 0xFF:
        raise ValueError("object_id is not between 0 and 0xFF.")


def validate_device_identification_object_value(value: bytes) -> None:
    """Validate a read-device-identification object value.

    Raises
    ------
    ValueError
        If ``value`` is too long for one object field in a Modbus PDU.

    """
    if len(value) > MAX_DEVICE_IDENTIFICATION_OBJECT_LENGTH:
        raise ValueError("object value is longer than 244 bytes.")


def pack_bits(values: list[bool]) -> bytes:
    """Pack boolean values into Modbus little-bit-order bytes.

    Parameters
    ----------
    values : list[bool]
        Boolean values to pack.

    Returns
    -------
    bytes
        Packed bit bytes.

    """
    payload = bytearray((len(values) + 7) // 8)
    for byte_index in range(len(payload)):
        base = byte_index * 8
        end = min(base + 8, len(values))
        byte = 0

        for value_index in range(base, end):
            if values[value_index]:
                byte |= _BITS_MASKS[value_index - base]

        payload[byte_index] = byte

    return bytes(payload)


def unpack_bits(data: bytes, count: int) -> list[bool]:
    """Unpack Modbus little-bit-order bytes into boolean values.

    Parameters
    ----------
    data : bytes
        Packed bit bytes.
    count : int
        Number of boolean values to return.

    Returns
    -------
    list[bool]
        Unpacked values.

    Raises
    ------
    ValueError
        If ``data`` does not contain enough bytes for ``count`` bits.

    """
    required_bytes = (count + 7) // 8
    if len(data) < required_bytes:
        raise ValueError("bit byte count is too short for requested count.")

    full_bytes, remaining_bits = divmod(count, 8)

    values: list[bool] = [
        bit for byte in data[:full_bytes] for bit in _UNPACKED_BITS_BY_BYTE[byte]
    ]
    if remaining_bits:
        values.extend(_UNPACKED_BITS_BY_BYTE[data[full_bytes]][:remaining_bits])

    return values


class RequestPDU(Protocol):
    """Protocol implemented by request PDU objects."""

    @property
    def function_code(self) -> int:
        """Return the Modbus function code."""
        ...

    def encode(self) -> bytes:
        """Encode the request PDU.

        Returns
        -------
        bytes
            Encoded request PDU.

        """
        ...


class ResponsePDU(Protocol):
    """Protocol implemented by response PDU objects."""

    @property
    def function_code(self) -> int:
        """Return the Modbus function code."""
        ...

    def encode(self) -> bytes:
        """Encode the response PDU."""
        ...


@dataclass(frozen=True)
class ReadCoilsRequest:
    """Read coils request PDU."""

    address: int
    count: int

    function_code: ClassVar[int] = 0x01

    def encode(self) -> bytes:
        """Encode the request PDU.

        Returns
        -------
        bytes
            Encoded request PDU.

        """
        return pack(">BHH", self.function_code, self.address, self.count)

    def __post_init__(self) -> None:
        """Validate the request fields."""
        validate_register_address(self.address)
        validate_bit_count(self.count)


@dataclass(frozen=True)
class ReadDiscreteInputsRequest:
    """Read discrete inputs request PDU."""

    address: int
    count: int

    function_code: ClassVar[int] = 0x02

    def encode(self) -> bytes:
        """Encode the request PDU.

        Returns
        -------
        bytes
            Encoded request PDU.

        """
        return pack(">BHH", self.function_code, self.address, self.count)

    def __post_init__(self) -> None:
        """Validate the request fields."""
        validate_register_address(self.address)
        validate_bit_count(self.count)


@dataclass(frozen=True)
class ReadBitsResponse:
    """Read coils or discrete inputs response PDU."""

    function_code: int
    values: list[bool]

    def encode(self) -> bytes:
        """Encode the response PDU.

        Returns
        -------
        bytes
            Encoded response PDU.

        """
        packed_values = pack_bits(self.values)
        return bytes([self.function_code, len(packed_values)]) + packed_values

    @classmethod
    def decode(
        cls, function_code: int, payload: bytes, count: int
    ) -> "ReadBitsResponse":
        """Decode a read-bits response payload.

        Parameters
        ----------
        function_code : int
            Response function code.
        payload : bytes
            Response payload after the function code.
        count : int
            Number of requested bits.

        Returns
        -------
        ReadBitsResponse
            Decoded response.

        Raises
        ------
        ValueError
            If the payload length or byte count is invalid.

        """
        if len(payload) == 0:
            raise ValueError("Length of payload is 0.")

        byte_count = payload[0]
        bit_bytes = payload[1:]
        if byte_count != len(bit_bytes):
            raise ValueError("Bit byte count does not match payload length")
        if byte_count < (count + 7) // 8:
            raise ValueError("Bit byte count is too short for requested count")

        return cls(function_code=function_code, values=unpack_bits(bit_bytes, count))


@dataclass(frozen=True)
class ReadHoldingRegistersRequest:
    """Read holding registers request PDU."""

    address: int
    count: int

    function_code: ClassVar[int] = 0x03

    def encode(self) -> bytes:
        """Encode the request PDU.

        Returns
        -------
        bytes
            Encoded request PDU.

        """
        return pack(">BHH", self.function_code, self.address, self.count)

    def __post_init__(self) -> None:
        """Validate the request fields."""
        validate_register_address(self.address)
        validate_register_count(self.count)


@dataclass(frozen=True)
class ReadInputRegistersRequest:
    """Read input registers request PDU."""

    address: int
    count: int

    function_code: ClassVar[int] = 0x04

    def encode(self) -> bytes:
        """Encode the request PDU.

        Returns
        -------
        bytes
            Encoded request PDU.

        """
        return pack(">BHH", self.function_code, self.address, self.count)

    def __post_init__(self) -> None:
        """Validate the request fields."""
        validate_register_address(self.address)
        validate_register_count(self.count)


@dataclass(frozen=True)
class ReadRegistersResponse:
    """Read holding or input registers response PDU."""

    function_code: int
    values: list[int]

    def encode(self) -> bytes:
        """Encode the response PDU.

        Returns
        -------
        bytes
            Encoded response PDU.

        """
        byte_count = len(self.values) * 2
        return pack(
            f">BB{len(self.values)}H", self.function_code, byte_count, *self.values
        )

    @classmethod
    def decode(cls, function_code: int, payload: bytes) -> "ReadRegistersResponse":
        """Decode a read-registers response payload.

        Parameters
        ----------
        function_code : int
            Response function code.
        payload : bytes
            Response payload after the function code.

        Returns
        -------
        ReadRegistersResponse
            Decoded response.

        Raises
        ------
        ValueError
            If the payload length or byte count is invalid.

        """
        if len(payload) == 0:
            raise ValueError("Length of payload is 0.")

        byte_count = payload[0]
        register_bytes = payload[1:]

        if byte_count != len(register_bytes):
            raise ValueError("Register byte count does not match payload length")
        if byte_count % 2 != 0:
            raise ValueError("Register byte count must be even")
        values = list(unpack(f">{byte_count // 2}H", register_bytes))

        return cls(function_code=function_code, values=values)


@dataclass(frozen=True)
class WriteSingleRegisterRequest:
    """Write single register request PDU."""

    address: int
    value: int

    function_code: ClassVar[int] = 0x06

    def encode(self) -> bytes:
        """Encode the request PDU.

        Returns
        -------
        bytes
            Encoded request PDU.

        """
        return pack(">BHH", self.function_code, self.address, self.value)

    def __post_init__(self) -> None:
        """Validate the request fields."""
        validate_register_address(self.address)
        validate_register_value(self.value)


@dataclass(frozen=True)
class WriteSingleRegisterResponse:
    """Write single register response PDU."""

    function_code: int
    address: int
    value: int

    def encode(self) -> bytes:
        """Encode the response PDU.

        Returns
        -------
        bytes
            Encoded response PDU.

        """
        return pack(">BHH", self.function_code, self.address, self.value)

    @classmethod
    def decode(cls, payload: bytes) -> "WriteSingleRegisterResponse":
        """Decode a write-single-register response payload.

        Parameters
        ----------
        payload : bytes
            Response payload after the function code.

        Returns
        -------
        WriteSingleRegisterResponse
            Decoded response.

        Raises
        ------
        ValueError
            If ``payload`` is not exactly four bytes.

        """
        # function code: Write Single Register
        # 00 05 address
        # 00 7B value
        if len(payload) != 4:
            raise ValueError()

        address, value = unpack(">HH", payload)

        return cls(function_code=0x06, address=address, value=value)


@dataclass(frozen=True)
class WriteSingleCoilRequest:
    """Write single coil request PDU."""

    address: int
    value: bool

    function_code: ClassVar[int] = 0x05

    def encode(self) -> bytes:
        """Encode the request PDU.

        Returns
        -------
        bytes
            Encoded request PDU.

        """
        encoded_value = COIL_ON if self.value else COIL_OFF
        return pack(">BHH", self.function_code, self.address, encoded_value)

    def __post_init__(self) -> None:
        """Validate the request fields.

        Raises
        ------
        ValueError
            If ``value`` is not a boolean.

        """
        validate_register_address(self.address)
        if type(self.value) is not bool:
            raise ValueError("coil value must be a bool.")


@dataclass(frozen=True)
class WriteSingleCoilResponse:
    """Write single coil response PDU."""

    function_code: int
    address: int
    value: bool

    def encode(self) -> bytes:
        """Encode the response PDU.

        Returns
        -------
        bytes
            Encoded response PDU.

        """
        encoded_value = COIL_ON if self.value else COIL_OFF
        return pack(">BHH", self.function_code, self.address, encoded_value)

    @classmethod
    def decode(cls, payload: bytes) -> "WriteSingleCoilResponse":
        """Decode a write-single-coil response payload.

        Parameters
        ----------
        payload : bytes
            Response payload after the function code.

        Returns
        -------
        WriteSingleCoilResponse
            Decoded response.

        Raises
        ------
        ValueError
            If ``payload`` length or encoded coil value is invalid.

        """
        if len(payload) != 4:
            raise ValueError()
        address, encoded_value = unpack(">HH", payload)
        if encoded_value == COIL_ON:
            value = True
        elif encoded_value == COIL_OFF:
            value = False
        else:
            raise ValueError("single coil echo value must be 0xFF00 or 0x0000")
        return cls(function_code=0x05, address=address, value=value)


@dataclass(frozen=True)
class WriteMultipleRegistersRequest:
    """Write multiple registers request PDU."""

    address: int
    values: list[int]

    function_code: ClassVar[int] = 0x10

    def encode(self) -> bytes:
        """Encode the request PDU.

        Returns
        -------
        bytes
            Encoded request PDU.

        """
        byte_count = len(self.values) * 2
        return pack(
            f">BHHB{len(self.values)}H",
            self.function_code,
            self.address,
            len(self.values),
            byte_count,
            *self.values,
        )

    def __post_init__(self) -> None:
        """Validate the request fields."""
        validate_register_address(self.address)
        validate_register_count(len(self.values), MAX_WRITE_REGISTERS)
        for value in self.values:
            validate_register_value(value)


@dataclass(frozen=True)
class WriteMultipleRegistersResponse:
    """Write multiple registers response PDU."""

    function_code: int
    address: int
    count: int

    def encode(self) -> bytes:
        """Encode the response PDU.

        Returns
        -------
        bytes
            Encoded response PDU.

        """
        return pack(">BHH", self.function_code, self.address, self.count)

    @classmethod
    def decode(cls, payload: bytes) -> "WriteMultipleRegistersResponse":
        """Decode a write-multiple-registers response payload.

        Parameters
        ----------
        payload : bytes
            Response payload after the function code.

        Returns
        -------
        WriteMultipleRegistersResponse
            Decoded response.

        Raises
        ------
        ValueError
            If ``payload`` is not exactly four bytes.

        """
        if len(payload) != 4:
            raise ValueError()
        address, count = unpack(">HH", payload)
        return cls(function_code=0x10, address=address, count=count)


@dataclass(frozen=True)
class WriteMultipleCoilsRequest:
    """Write multiple coils request PDU."""

    address: int
    values: list[bool]

    function_code: ClassVar[int] = 0x0F

    def encode(self) -> bytes:
        """Encode the request PDU.

        Returns
        -------
        bytes
            Encoded request PDU.

        """
        packed_values = pack_bits(self.values)
        return (
            pack(
                ">BHHB",
                self.function_code,
                self.address,
                len(self.values),
                len(packed_values),
            )
            + packed_values
        )

    def __post_init__(self) -> None:
        """Validate the request fields.

        Raises
        ------
        ValueError
            If any coil value is not a boolean.

        """
        validate_register_address(self.address)
        validate_bit_count(len(self.values), MAX_WRITE_BITS)
        for value in self.values:
            if type(value) is not bool:
                raise ValueError("coil values must be bools.")


@dataclass(frozen=True)
class WriteMultipleCoilsResponse:
    """Write multiple coils response PDU."""

    function_code: int
    address: int
    count: int

    def encode(self) -> bytes:
        """Encode the response PDU.

        Returns
        -------
        bytes
            Encoded response PDU.

        """
        return pack(">BHH", self.function_code, self.address, self.count)

    @classmethod
    def decode(cls, payload: bytes) -> "WriteMultipleCoilsResponse":
        """Decode a write-multiple-coils response payload.

        Parameters
        ----------
        payload : bytes
            Response payload after the function code.

        Returns
        -------
        WriteMultipleCoilsResponse
            Decoded response.

        Raises
        ------
        ValueError
            If ``payload`` is not exactly four bytes.

        """
        if len(payload) != 4:
            raise ValueError()
        address, count = unpack(">HH", payload)
        return cls(function_code=0x0F, address=address, count=count)


@dataclass(frozen=True)
class MaskWriteRegisterRequest:
    """Mask write register request PDU."""

    address: int
    and_mask: int
    or_mask: int

    function_code: ClassVar[int] = 0x16

    def encode(self) -> bytes:
        """Encode the request PDU.

        Returns
        -------
        bytes
            Encoded request PDU.

        """
        return pack(
            ">BHHH",
            self.function_code,
            self.address,
            self.and_mask,
            self.or_mask,
        )

    def __post_init__(self) -> None:
        """Validate the request fields."""
        validate_register_address(self.address)
        validate_register_value(self.and_mask)
        validate_register_value(self.or_mask)


@dataclass(frozen=True)
class MaskWriteRegisterResponse:
    """Mask write register response PDU."""

    function_code: int
    address: int
    and_mask: int
    or_mask: int

    def encode(self) -> bytes:
        """Encode the response PDU.

        Returns
        -------
        bytes
            Encoded response PDU.

        """
        return pack(
            ">BHHH",
            self.function_code,
            self.address,
            self.and_mask,
            self.or_mask,
        )

    @classmethod
    def decode(cls, payload: bytes) -> "MaskWriteRegisterResponse":
        """Decode a mask-write-register response payload.

        Parameters
        ----------
        payload : bytes
            Response payload after the function code.

        Returns
        -------
        MaskWriteRegisterResponse
            Decoded response.

        Raises
        ------
        ValueError
            If ``payload`` is not exactly six bytes.

        """
        if len(payload) != 6:
            raise ValueError()
        address, and_mask, or_mask = unpack(">HHH", payload)
        return cls(
            function_code=0x16,
            address=address,
            and_mask=and_mask,
            or_mask=or_mask,
        )


@dataclass(frozen=True)
class ReadWriteMultipleRegistersRequest:
    """Read/write multiple registers request PDU."""

    read_address: int
    read_count: int
    write_address: int
    values: list[int]

    function_code: ClassVar[int] = 0x17

    def encode(self) -> bytes:
        """Encode the request PDU.

        Returns
        -------
        bytes
            Encoded request PDU.

        """
        byte_count = len(self.values) * 2
        return pack(
            f">BHHHHB{len(self.values)}H",
            self.function_code,
            self.read_address,
            self.read_count,
            self.write_address,
            len(self.values),
            byte_count,
            *self.values,
        )

    def __post_init__(self) -> None:
        """Validate the request fields."""
        validate_register_address(self.read_address)
        validate_register_count(self.read_count)
        validate_register_address(self.write_address)
        validate_register_count(len(self.values), MAX_READ_WRITE_REGISTERS_WRITE)
        for value in self.values:
            validate_register_value(value)


class DeviceIdentificationReadCode(IntEnum):
    """Read device identification access codes."""

    BASIC = 0x01
    REGULAR = 0x02
    EXTENDED = 0x03
    SPECIFIC = 0x04


class DeviceIdentificationConformityLevel(IntEnum):
    """Read device identification conformity levels."""

    BASIC = 0x01
    REGULAR = 0x02
    EXTENDED = 0x03
    BASIC_INDIVIDUAL = 0x81
    REGULAR_INDIVIDUAL = 0x82
    EXTENDED_INDIVIDUAL = 0x83


@dataclass(frozen=True)
class DeviceIdentificationObject:
    """One read-device-identification object."""

    object_id: int
    value: bytes

    def __post_init__(self) -> None:
        """Validate object fields."""
        validate_device_identification_object_id(self.object_id)
        validate_device_identification_object_value(self.value)


@dataclass(frozen=True)
class ReadDeviceIdentificationRequest:
    """Read Device Identification request PDU for MEI type ``0x0E``."""

    read_code: int
    object_id: int = 0
    mei_type: int = READ_DEVICE_IDENTIFICATION_MEI_TYPE

    function_code: ClassVar[int] = 0x2B

    def encode(self) -> bytes:
        """Encode the request PDU.

        Returns
        -------
        bytes
            Encoded request PDU.

        """
        return bytes(
            [self.function_code, self.mei_type, self.read_code, self.object_id]
        )

    def __post_init__(self) -> None:
        """Validate the request fields.

        Raises
        ------
        ValueError
            If any request field is outside the supported range.

        """
        if self.mei_type != READ_DEVICE_IDENTIFICATION_MEI_TYPE:
            raise ValueError("MEI type must be 0x0E for Read Device Identification.")
        try:
            DeviceIdentificationReadCode(self.read_code)
        except ValueError as exc:
            raise ValueError("read_code must be between 0x01 and 0x04.") from exc
        validate_device_identification_object_id(self.object_id)


@dataclass(frozen=True)
class ReadDeviceIdentificationResponse:
    """Read Device Identification response PDU for MEI type ``0x0E``."""

    read_code: int
    conformity_level: int
    objects: list[DeviceIdentificationObject]
    more_follows: bool = False
    next_object_id: int = 0
    mei_type: int = READ_DEVICE_IDENTIFICATION_MEI_TYPE

    function_code: ClassVar[int] = 0x2B

    def encode(self) -> bytes:
        """Encode the response PDU.

        Returns
        -------
        bytes
            Encoded response PDU.

        """
        payload = bytearray(
            [
                self.function_code,
                self.mei_type,
                self.read_code,
                self.conformity_level,
                0xFF if self.more_follows else 0x00,
                self.next_object_id,
                len(self.objects),
            ]
        )
        for item in self.objects:
            payload.extend((item.object_id, len(item.value)))
            payload.extend(item.value)
        return bytes(payload)

    def __post_init__(self) -> None:
        """Validate response fields.

        Raises
        ------
        ValueError
            If any response field is outside the supported range.

        """
        if self.mei_type != READ_DEVICE_IDENTIFICATION_MEI_TYPE:
            raise ValueError("MEI type must be 0x0E for Read Device Identification.")
        try:
            DeviceIdentificationReadCode(self.read_code)
        except ValueError as exc:
            raise ValueError("read_code must be between 0x01 and 0x04.") from exc
        try:
            DeviceIdentificationConformityLevel(self.conformity_level)
        except ValueError as exc:
            raise ValueError("invalid conformity level.") from exc
        validate_device_identification_object_id(self.next_object_id)
        if len(self.objects) > 0xFF:
            raise ValueError("too many device identification objects.")
        for item in self.objects:
            if not isinstance(item, DeviceIdentificationObject):
                raise ValueError("objects must be DeviceIdentificationObject values.")

    @classmethod
    def decode(cls, payload: bytes) -> "ReadDeviceIdentificationResponse":
        """Decode a read-device-identification response payload.

        Parameters
        ----------
        payload : bytes
            Response payload after the function code.

        Returns
        -------
        ReadDeviceIdentificationResponse
            Decoded response.

        Raises
        ------
        ValueError
            If the payload is malformed.

        """
        if len(payload) < 6:
            raise ValueError("read device identification response is too short.")

        mei_type, read_code, conformity_level, more_follows, next_object_id, count = (
            payload[:6]
        )
        if mei_type != READ_DEVICE_IDENTIFICATION_MEI_TYPE:
            raise ValueError("MEI type must be 0x0E for Read Device Identification.")
        if more_follows not in (0x00, 0xFF):
            raise ValueError("more_follows must be 0x00 or 0xFF.")

        objects: list[DeviceIdentificationObject] = []
        offset = 6
        for _ in range(count):
            if len(payload) - offset < 2:
                raise ValueError("device identification object header is incomplete.")
            object_id = payload[offset]
            length = payload[offset + 1]
            offset += 2
            if len(payload) - offset < length:
                raise ValueError("device identification object value is incomplete.")
            objects.append(
                DeviceIdentificationObject(
                    object_id=object_id,
                    value=payload[offset : offset + length],
                )
            )
            offset += length

        if offset != len(payload):
            raise ValueError("extra bytes after device identification objects.")

        return cls(
            mei_type=mei_type,
            read_code=read_code,
            conformity_level=conformity_level,
            more_follows=more_follows == 0xFF,
            next_object_id=next_object_id,
            objects=objects,
        )


@dataclass(frozen=True)
class ExceptionResponse:
    """Modbus exception response PDU."""

    function_code: int
    exception_code: int

    def encode(self) -> bytes:
        """Encode the exception response PDU.

        Returns
        -------
        bytes
            Encoded exception response PDU.

        """
        return bytes([self.function_code | 0x80, self.exception_code])

    @classmethod
    def decode(cls, function_code: int, payload: bytes) -> "ExceptionResponse":
        """Decode an exception response payload.

        Parameters
        ----------
        function_code : int
            Exception response function code.
        payload : bytes
            Response payload after the function code.

        Returns
        -------
        ExceptionResponse
            Decoded exception response.

        Raises
        ------
        ValueError
            If ``payload`` is not exactly one byte.

        """
        if len(payload) != 1:
            raise ValueError()
        exception_code = payload[0]
        return cls(function_code & 0x7F, exception_code=exception_code)


def decode_response_pdu(data: bytes, request: RequestPDU) -> ResponsePDU:
    """Decode response bytes using the original request context.

    Parameters
    ----------
    data : bytes
        Encoded response PDU bytes.
    request : RequestPDU
        Original request PDU.

    Returns
    -------
    ResponsePDU
        Decoded response PDU.

    Raises
    ------
    ValueError
        If the response is empty, mismatched, malformed, or unsupported.

    """
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

    if function_code in (FunctionCode.READ_COILS, FunctionCode.READ_DISCRETE_INPUTS):
        if not isinstance(request, (ReadCoilsRequest, ReadDiscreteInputsRequest)):
            raise ValueError()
        return ReadBitsResponse.decode(function_code, payload, request.count)
    if function_code in (
        FunctionCode.READ_HOLDING_REGISTERS,
        FunctionCode.READ_INPUT_REGISTERS,
    ):
        return ReadRegistersResponse.decode(function_code, payload)
    if function_code == FunctionCode.READ_WRITE_MULTIPLE_REGISTERS:
        if not isinstance(request, ReadWriteMultipleRegistersRequest):
            raise ValueError()
        response = ReadRegistersResponse.decode(function_code, payload)
        if len(response.values) != request.read_count:
            raise ValueError("read register response count does not match request")
        return response
    if function_code == FunctionCode.ENCAPSULATED_INTERFACE_TRANSPORT and isinstance(
        request, ReadDeviceIdentificationRequest
    ):
        response = ReadDeviceIdentificationResponse.decode(payload)
        if response.read_code != request.read_code:
            raise ValueError("read device identification response code mismatch")
        return response
    if function_code == FunctionCode.WRITE_SINGLE_COIL:
        return WriteSingleCoilResponse.decode(payload)
    if function_code == FunctionCode.WRITE_SINGLE_REGISTER:
        return WriteSingleRegisterResponse.decode(payload)
    if function_code == FunctionCode.WRITE_MULTIPLE_COILS:
        return WriteMultipleCoilsResponse.decode(payload)
    if function_code == FunctionCode.WRITE_MULTIPLE_REGISTERS:
        return WriteMultipleRegistersResponse.decode(payload)
    if function_code == FunctionCode.MASK_WRITE_REGISTER:
        return MaskWriteRegisterResponse.decode(payload)
    else:
        custom_response = default_function_code_registry.decode_response(
            function_code=function_code,
            payload=payload,
            request=request,
        )
        if custom_response is not None:
            return custom_response
        raise ValueError()


def decode_request_pdu(data: bytes) -> RequestPDU:
    """Decode request PDU bytes.

    Parameters
    ----------
    data : bytes
        Encoded request PDU bytes.

    Returns
    -------
    RequestPDU
        Decoded request PDU.

    Raises
    ------
    ModbusPDUError
        If the function code is unsupported.
    ValueError
        If the PDU is empty or malformed.

    """
    if len(data) == 0:
        raise ValueError("PDU is empty")

    function_code = data[0]
    payload = data[1:]

    if function_code in (
        FunctionCode.READ_COILS,
        FunctionCode.READ_DISCRETE_INPUTS,
        FunctionCode.READ_HOLDING_REGISTERS,
        FunctionCode.READ_INPUT_REGISTERS,
    ):
        if len(payload) != 4:
            raise ValueError("read request payload must be 4 bytes")
        address, count = unpack(">HH", payload)
        if function_code == FunctionCode.READ_COILS:
            return ReadCoilsRequest(address=address, count=count)
        if function_code == FunctionCode.READ_DISCRETE_INPUTS:
            return ReadDiscreteInputsRequest(address=address, count=count)
        if function_code == FunctionCode.READ_HOLDING_REGISTERS:
            return ReadHoldingRegistersRequest(address=address, count=count)
        return ReadInputRegistersRequest(address=address, count=count)

    if function_code == FunctionCode.WRITE_SINGLE_COIL:
        if len(payload) != 4:
            raise ValueError("write single coil request payload must be 4 bytes")
        address, encoded_value = unpack(">HH", payload)
        if encoded_value == COIL_ON:
            return WriteSingleCoilRequest(address=address, value=True)
        if encoded_value == COIL_OFF:
            return WriteSingleCoilRequest(address=address, value=False)
        raise ValueError("single coil value must be 0xFF00 or 0x0000")

    if function_code == FunctionCode.WRITE_SINGLE_REGISTER:
        if len(payload) != 4:
            raise ValueError("write single register request payload must be 4 bytes")
        address, value = unpack(">HH", payload)
        return WriteSingleRegisterRequest(address=address, value=value)

    if function_code == FunctionCode.WRITE_MULTIPLE_COILS:
        if len(payload) < 5:
            raise ValueError("write multiple coils request payload is too short")

        address, count = unpack_from(">HH", payload)
        byte_count = payload[4]
        bit_bytes = payload[5:]

        if byte_count != len(bit_bytes):
            raise ValueError("coil byte count does not match payload length")
        if byte_count < (count + 7) // 8:
            raise ValueError("coil byte count is too short for requested count")

        values = unpack_bits(bit_bytes, count)
        return WriteMultipleCoilsRequest(address=address, values=values)

    if function_code == FunctionCode.WRITE_MULTIPLE_REGISTERS:
        if len(payload) < 5:
            raise ValueError("write multiple registers request payload is too short")

        address, count = unpack_from(">HH", payload)
        byte_count = payload[4]
        register_bytes = payload[5:]

        if byte_count != len(register_bytes):
            raise ValueError("register byte count does not match payload length")
        if byte_count % 2 != 0:
            raise ValueError("register byte count must be even")
        if count != byte_count // 2:
            raise ValueError("register count does not match byte count")

        values = list(unpack(f">{byte_count // 2}H", register_bytes))
        return WriteMultipleRegistersRequest(address=address, values=values)

    if function_code == FunctionCode.MASK_WRITE_REGISTER:
        if len(payload) != 6:
            raise ValueError("mask write register request payload must be 6 bytes")
        address, and_mask, or_mask = unpack(">HHH", payload)
        return MaskWriteRegisterRequest(
            address=address,
            and_mask=and_mask,
            or_mask=or_mask,
        )

    if function_code == FunctionCode.READ_WRITE_MULTIPLE_REGISTERS:
        if len(payload) < 9:
            raise ValueError(
                "read/write multiple registers request payload is too short"
            )

        read_address, read_count, write_address, write_count = unpack_from(
            ">HHHH", payload
        )
        byte_count = payload[8]
        register_bytes = payload[9:]

        if byte_count != len(register_bytes):
            raise ValueError("register byte count does not match payload length")
        if byte_count % 2 != 0:
            raise ValueError("register byte count must be even")
        if write_count != byte_count // 2:
            raise ValueError("register count does not match byte count")

        values = list(unpack(f">{byte_count // 2}H", register_bytes))
        return ReadWriteMultipleRegistersRequest(
            read_address=read_address,
            read_count=read_count,
            write_address=write_address,
            values=values,
        )
    if function_code == FunctionCode.ENCAPSULATED_INTERFACE_TRANSPORT:
        if len(payload) == 3 and payload[0] == READ_DEVICE_IDENTIFICATION_MEI_TYPE:
            mei_type, read_code, object_id = payload
            return ReadDeviceIdentificationRequest(
                mei_type=mei_type,
                read_code=read_code,
                object_id=object_id,
            )
        if len(payload) > 0 and payload[0] == READ_DEVICE_IDENTIFICATION_MEI_TYPE:
            raise ValueError(
                "read device identification request payload must be 3 bytes"
            )

    custom_request = default_function_code_registry.decode_request(
        function_code=function_code,
        payload=payload,
    )
    if custom_request is not None:
        return custom_request
    raise ModbusPDUError(f"Unsupported function code: {function_code}")
