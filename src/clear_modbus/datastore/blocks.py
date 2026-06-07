"""Contiguous datastore blocks for register and bit data areas."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from clear_modbus.datastore.errors import (
    InvalidAddressError,
    InvalidValueError,
    ReadOnlyDataBlockError,
)

__all__ = ["BitBlock", "RegisterBlock"]


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
        """Return the inclusive final address covered by this block.

        Returns
        -------
        int
            Last address in the block. Empty blocks return one less than
            ``start_address``.

        """
        return self.start_address + len(self.values) - 1

    def contains(self, address: int, count: int = 1) -> bool:
        """Return whether the full address range is inside the block.

        Parameters
        ----------
        address : int
            First requested address.
        count : int, optional
            Number of values in the requested range.

        Returns
        -------
        bool
            ``True`` when every requested address is covered.

        """
        return (
            count > 0
            and address >= self.start_address
            and address + count - 1 <= self.end_address
        )

    def read(self, address: int, count: int) -> list[int]:
        """Read register values from the block.

        Parameters
        ----------
        address : int
            First register address to read.
        count : int
            Number of register values to read.

        Returns
        -------
        list[int]
            Copy of the requested register values.

        Raises
        ------
        InvalidAddressError
            If the requested range is outside the block.

        """
        if not self.contains(address, count):
            raise InvalidAddressError(address)
        offset = self.offset_for(address)
        return self.values[offset : offset + count]

    def write(self, address: int, values: Sequence[object]) -> None:
        """Write register values into the block.

        Parameters
        ----------
        address : int
            First register address to write.
        values : Sequence[object]
            Register values to write.

        Raises
        ------
        ReadOnlyDataBlockError
            If the block is read-only.
        InvalidAddressError
            If the write range is outside the block.
        InvalidValueError
            If any value is not an integer in the range ``0`` through
            ``0xFFFF``.

        """
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
        """Convert a Modbus address to a zero-based list offset.

        Parameters
        ----------
        address : int
            Address inside the block.

        Returns
        -------
        int
            Offset into ``values``.

        Raises
        ------
        InvalidAddressError
            If ``address`` is outside the block.

        """
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
        """Return the inclusive final address covered by this block.

        Returns
        -------
        int
            Last address in the block. Empty blocks return one less than
            ``start_address``.

        """
        return self.start_address + len(self.values) - 1

    def contains(self, address: int, count: int = 1) -> bool:
        """Return whether the full bit range is inside the block.

        Parameters
        ----------
        address : int
            First requested address.
        count : int, optional
            Number of bits in the requested range.

        Returns
        -------
        bool
            ``True`` when every requested address is covered.

        """
        return (
            count > 0
            and address >= self.start_address
            and address + count - 1 <= self.end_address
        )

    def read(self, address: int, count: int) -> list[bool]:
        """Read bit values from the block.

        Parameters
        ----------
        address : int
            First bit address to read.
        count : int
            Number of bit values to read.

        Returns
        -------
        list[bool]
            Copy of the requested bit values.

        Raises
        ------
        InvalidAddressError
            If the requested range is outside the block.

        """
        if not self.contains(address, count):
            raise InvalidAddressError(address)
        offset = self.offset_for(address)
        return self.values[offset : offset + count]

    def write(self, address: int, values: Sequence[object]) -> None:
        """Write bit values into the block.

        Parameters
        ----------
        address : int
            First bit address to write.
        values : Sequence[object]
            Boolean values to write.

        Raises
        ------
        ReadOnlyDataBlockError
            If the block is read-only.
        InvalidAddressError
            If the write range is outside the block.
        InvalidValueError
            If any value is not a boolean.

        """
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
        """Convert a Modbus bit address to a zero-based list offset.

        Parameters
        ----------
        address : int
            Address inside the block.

        Returns
        -------
        int
            Offset into ``values``.

        Raises
        ------
        InvalidAddressError
            If ``address`` is outside the block.

        """
        if not self.contains(address):
            raise InvalidAddressError(address)
        return address - self.start_address
