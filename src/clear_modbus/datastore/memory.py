"""In-memory Modbus datastore implementation."""

from bisect import bisect_right
from collections.abc import Sequence
from typing import TypeVar

from clear_modbus.datastore import InvalidAddressError
from clear_modbus.datastore.blocks import BitBlock, DataBlock, RegisterBlock

__all__ = ["MemoryDataStore"]


BlockT = TypeVar("BlockT", bound=DataBlock)


class MemoryDataStore:
    """Store Modbus data areas in immutable collections of contiguous blocks.

    Parameters
    ----------
    holding_registers : list[RegisterBlock] | None
        Blocks backing function codes ``0x03`` and ``0x10``. Blocks are sorted
        and stored as an immutable tuple during construction.
    input_registers : list[RegisterBlock] | None
        Blocks backing function code ``0x04``. Blocks are sorted and stored as
        an immutable tuple during construction.
    coils : list[BitBlock] | None
        Blocks backing function codes ``0x01``, ``0x05``, and ``0x0F``.
        Blocks are sorted and stored as an immutable tuple during construction.
    discrete_inputs : list[BitBlock] | None
        Blocks backing function code ``0x02``. Blocks are sorted and stored as
        an immutable tuple during construction.

    Attributes
    ----------
    holding_registers : tuple[RegisterBlock, ...]
        Blocks backing function codes ``0x03`` and ``0x10``.
    input_registers : tuple[RegisterBlock, ...]
        Blocks backing function code ``0x04``.
    coils : tuple[BitBlock, ...]
        Blocks backing function codes ``0x01``, ``0x05``, and ``0x0F``.
    discrete_inputs : tuple[BitBlock, ...]
        Blocks backing function code ``0x02``.

    Notes
    -----
    Block collections are fixed after construction. Update values through the
    datastore methods or the block ``write`` methods rather than adding,
    removing, reordering, or changing block address ranges after construction.

    """

    holding_registers: tuple[RegisterBlock, ...]
    input_registers: tuple[RegisterBlock, ...]
    coils: tuple[BitBlock, ...]
    discrete_inputs: tuple[BitBlock, ...]

    def __init__(
        self,
        holding_registers: list[RegisterBlock] | None = None,
        input_registers: list[RegisterBlock] | None = None,
        coils: list[BitBlock] | None = None,
        discrete_inputs: list[BitBlock] | None = None,
    ) -> None:
        self.holding_registers = tuple(
            sorted(
                holding_registers if holding_registers is not None else [],
                key=lambda block: block.start_address,
            )
        )
        self.input_registers = tuple(
            sorted(
                input_registers if input_registers is not None else [],
                key=lambda block: block.start_address,
            )
        )
        self.coils = tuple(
            sorted(
                coils if coils is not None else [],
                key=lambda block: block.start_address,
            )
        )
        self.discrete_inputs = tuple(
            sorted(
                discrete_inputs if discrete_inputs is not None else [],
                key=lambda block: block.start_address,
            )
        )
        self._holding_register_blocks, self._holding_register_starts = (
            self._index_blocks(self.holding_registers)
        )
        self._input_register_blocks, self._input_register_starts = self._index_blocks(
            self.input_registers
        )
        self._coils_blocks, self._coils_starts = self._index_blocks(self.coils)
        self._discrete_inputs_blocks, self._discrete_inputs_starts = self._index_blocks(
            self.discrete_inputs
        )
        _validate_no_overlapping_register_blocks(self.holding_registers)
        _validate_no_overlapping_register_blocks(self.input_registers)
        _validate_no_overlapping_bit_blocks(self.coils)
        _validate_no_overlapping_bit_blocks(self.discrete_inputs)

    def get_holding_registers(self, address: int, count: int) -> list[int]:
        """Return holding-register values.

        Parameters
        ----------
        address : int
            First holding-register address.
        count : int
            Number of registers to read.

        Returns
        -------
        list[int]
            Register values.

        """
        block = self._find_block(
            self._holding_register_blocks, self._holding_register_starts, address, count
        )
        return block.read(address, count)

    def set_holding_registers(self, address: int, values: list[int]) -> None:
        """Write holding-register values."""
        block = self._find_block(
            self._holding_register_blocks,
            self._holding_register_starts,
            address,
            len(values),
        )
        block.write(address, values)

    def get_input_registers(self, address: int, count: int) -> list[int]:
        """Return input-register values.

        Parameters
        ----------
        address : int
            First input-register address.
        count : int
            Number of registers to read.

        Returns
        -------
        list[int]
            Register values.

        """
        block = self._find_block(
            self._input_register_blocks, self._input_register_starts, address, count
        )
        return block.read(address, count)

    def get_coils(self, address: int, count: int) -> list[bool]:
        """Return coil values.

        Parameters
        ----------
        address : int
            First coil address.
        count : int
            Number of coils to read.

        Returns
        -------
        list[bool]
            Coil values.

        """
        block = self._find_block(self._coils_blocks, self._coils_starts, address, count)
        return block.read(address, count)

    def set_coils(self, address: int, values: list[bool]) -> None:
        """Write coil values."""
        block = self._find_block(
            self._coils_blocks, self._coils_starts, address, len(values)
        )
        block.write(address, values)

    def get_discrete_inputs(self, address: int, count: int) -> list[bool]:
        """Return discrete-input values.

        Parameters
        ----------
        address : int
            First discrete-input address.
        count : int
            Number of inputs to read.

        Returns
        -------
        list[bool]
            Discrete-input values.

        """
        block = self._find_block(
            self._discrete_inputs_blocks, self._discrete_inputs_starts, address, count
        )
        return block.read(address, count)

    def _find_block(
        self, blocks: Sequence[BlockT], starts: Sequence[int], address: int, count: int
    ) -> BlockT:
        index = bisect_right(starts, address) - 1
        if index >= 0:
            block = blocks[index]
            if block.contains(address, count):
                return block

        raise InvalidAddressError(address, count)

    def _index_blocks(
        self, blocks: Sequence[BlockT]
    ) -> tuple[tuple[BlockT, ...], list[int]]:
        indexed_blocks = tuple(block for block in blocks if len(block.values) > 0)
        starts = [block.start_address for block in indexed_blocks]
        return indexed_blocks, starts


def _validate_no_overlapping_register_blocks(
    blocks: Sequence[RegisterBlock],
) -> None:
    ranges = [
        (block.start_address, block.end_address)
        for block in blocks
        if len(block.values) > 0
    ]
    _validate_no_overlapping_ranges(ranges)


def _validate_no_overlapping_bit_blocks(blocks: Sequence[BitBlock]) -> None:
    ranges = [
        (block.start_address, block.end_address)
        for block in blocks
        if len(block.values) > 0
    ]
    _validate_no_overlapping_ranges(ranges)


def _validate_no_overlapping_ranges(ranges: list[tuple[int, int]]) -> None:
    sorted_ranges = sorted(ranges)
    for previous, current in zip(sorted_ranges, sorted_ranges[1:]):
        previous_start, previous_end = previous
        current_start, current_end = current
        if current_start <= previous_end:
            raise ValueError(
                "Datastore blocks must not overlap: "
                f"{previous_start}-{previous_end} overlaps "
                f"{current_start}-{current_end}."
            )
