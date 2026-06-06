from dataclasses import dataclass, field
from typing import Sequence

from modbus.datastore.errors import InvalidAddressError, InvalidValueError, ReadOnlyDataBlockError


@dataclass
class RegisterBlock:
    """A contiguous range of 16-bit Modbus register values.

    Example:
        RegisterBlock(start_address=100, values=[10, 20, 30])

    Represents:
        address 100 -> 10
        address 101 -> 20
        address 102 -> 30

    A read of address=101, count=2 should return [20, 30].
    A write of address=101, values=[55, 66] should change the block to
    [10, 55, 66].
    """

    start_address: int
    values: list[int] = field(default_factory=list)
    readonly: bool = False

    @property
    def end_address(self) -> int:
        return self.start_address + len(self.values) - 1

    def contains(self, address: int, count: int = 1) -> bool:
        return (
            count > 0
            and address >= self.start_address
            and address + count - 1 <= self.end_address
        )

    def read(self, address: int, count: int) -> list[int]:
        if not self.contains(address, count):
            raise InvalidAddressError(address)
        offset = self.offset_for(address)
        return self.values[offset : offset + count]

    def write(self, address: int, values: Sequence[object]) -> None:
        if self.readonly:
            raise ReadOnlyDataBlockError(address)
        if not self.contains(address, len(values)):
            raise InvalidAddressError(address)
        offset = self.offset_for(address)
        validated_values: list[int] = []
        for value in values:
            if type(value) is not int:
                raise InvalidValueError(value)
            if not 0 <= value <= 0xFFFF:
                raise InvalidValueError(value)
            validated_values.append(value)
        self.values[offset : offset + len(validated_values)] = validated_values

    def offset_for(self, address: int) -> int:
        if not self.contains(address):
            raise InvalidAddressError(address)
        return address - self.start_address


@dataclass
class BitBlock:
    """A contiguous range of Modbus bit values for coils or discrete inputs.

    Example:
        BitBlock(start_address=0, values=[True, False, True])

    Represents:
        address 0 -> True
        address 1 -> False
        address 2 -> True

    A read of address=1, count=2 should return [False, True].
    A write of address=1, values=[True, True] should change the block to
    [True, True, True].
    """

    start_address: int
    values: list[bool] = field(default_factory=list)
    readonly: bool = False

    @property
    def end_address(self) -> int:
        return self.start_address + len(self.values) - 1

    def contains(self, address: int, count: int = 1) -> bool:
        return (
            count > 0
            and address >= self.start_address
            and address + count - 1 <= self.end_address
        )

    def read(self, address: int, count: int) -> list[bool]:
        if not self.contains(address, count):
            raise InvalidAddressError(address)
        offset = self.offset_for(address)
        return self.values[offset : offset + count]

    def write(self, address: int, values: Sequence[object]) -> None:
        if self.readonly:
            raise ReadOnlyDataBlockError(address)
        if not self.contains(address, len(values)):
            raise InvalidAddressError(address)
        offset = self.offset_for(address)
        validated_values: list[bool] = []
        for value in values:
            if type(value) is not bool:
                raise InvalidValueError(value)
            validated_values.append(value)
        self.values[offset : offset + len(validated_values)] = validated_values

    def offset_for(self, address: int) -> int:
        if not self.contains(address):
            raise InvalidAddressError(address)
        return address - self.start_address
