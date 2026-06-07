"""In-memory Modbus datastore implementation."""

from clear_modbus.datastore import InvalidAddressError
from clear_modbus.datastore.blocks import BitBlock, RegisterBlock


class MemoryDataStore:
    """Store Modbus data areas in lists of contiguous blocks.

    Parameters
    ----------
    holding_registers : list[RegisterBlock] | None
        Blocks backing function codes ``0x03`` and ``0x10``.
    input_registers : list[RegisterBlock] | None
        Blocks backing function code ``0x04``.
    coils : list[BitBlock] | None
        Blocks backing function codes ``0x01``, ``0x05``, and ``0x0F``.
    discrete_inputs : list[BitBlock] | None
        Blocks backing function code ``0x02``.

    Attributes
    ----------
    holding_registers : list[RegisterBlock]
        Blocks backing function codes ``0x03`` and ``0x10``.
    input_registers : list[RegisterBlock]
        Blocks backing function code ``0x04``.
    coils : list[BitBlock]
        Blocks backing function codes ``0x01``, ``0x05``, and ``0x0F``.
    discrete_inputs : list[BitBlock]
        Blocks backing function code ``0x02``.

    """

    holding_registers: list[RegisterBlock]
    input_registers: list[RegisterBlock]
    coils: list[BitBlock]
    discrete_inputs: list[BitBlock]

    def __init__(
        self,
        holding_registers: list[RegisterBlock] | None = None,
        input_registers: list[RegisterBlock] | None = None,
        coils: list[BitBlock] | None = None,
        discrete_inputs: list[BitBlock] | None = None,
    ) -> None:
        self.holding_registers = (
            holding_registers if holding_registers is not None else []
        )
        self.input_registers = input_registers if input_registers is not None else []
        self.coils = coils if coils is not None else []
        self.discrete_inputs = discrete_inputs if discrete_inputs is not None else []
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
        block = self._find_register_block(self.holding_registers, address, count)
        return block.read(address, count)

    def set_holding_registers(self, address: int, values: list[int]) -> None:
        """Write holding-register values."""
        block = self._find_register_block(self.holding_registers, address, len(values))
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
        block = self._find_register_block(self.input_registers, address, count)
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
        block = self._find_bit_block(self.coils, address, count)
        return block.read(address, count)

    def set_coils(self, address: int, values: list[bool]) -> None:
        """Write coil values."""
        block = self._find_bit_block(self.coils, address, len(values))
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
        block = self._find_bit_block(self.discrete_inputs, address, count)
        return block.read(address, count)

    def _find_register_block(
        self,
        blocks: list[RegisterBlock],
        address: int,
        count: int,
    ) -> RegisterBlock:
        for block in blocks:
            if block.contains(address, count):
                return block

        raise InvalidAddressError(address, count)

    def _find_bit_block(
        self,
        blocks: list[BitBlock],
        address: int,
        count: int,
    ) -> BitBlock:
        for block in blocks:
            if block.contains(address, count):
                return block

        raise InvalidAddressError(address, count)


def _validate_no_overlapping_register_blocks(blocks: list[RegisterBlock]) -> None:
    ranges = [
        (block.start_address, block.end_address)
        for block in blocks
        if len(block.values) > 0
    ]
    _validate_no_overlapping_ranges(ranges)


def _validate_no_overlapping_bit_blocks(blocks: list[BitBlock]) -> None:
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
