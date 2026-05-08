from modbus.datastore import InvalidAddressError
from modbus.datastore.blocks import BitBlock, RegisterBlock


class MemoryDataStore:
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
        # TODO: Decide whether overlapping blocks should be rejected during initialization.
        self.holding_registers = holding_registers if holding_registers is not None else []
        self.input_registers = input_registers if input_registers is not None else []
        self.coils = coils if coils is not None else []
        self.discrete_inputs = discrete_inputs if discrete_inputs is not None else []

    def get_holding_registers(self, address: int, count: int) -> list[int]:
        block = self._find_register_block(self.holding_registers, address, count)
        return block.read(address, count)

    def set_holding_registers(self, address: int, values: list[int]) -> None:
        block = self._find_register_block(self.holding_registers, address, len(values))
        block.write(address, values)

    def get_input_registers(self, address: int, count: int) -> list[int]:
        block = self._find_register_block(self.input_registers, address, count)
        return block.read(address, count)

    def get_coils(self, address: int, count: int) -> list[bool]:
        block = self._find_bit_block(self.coils, address, count)
        return block.read(address, count)

    def set_coils(self, address: int, values: list[bool]) -> None:
        block = self._find_bit_block(self.coils, address, len(values))
        block.write(address, values)

    def get_discrete_inputs(self, address: int, count: int) -> list[bool]:
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
