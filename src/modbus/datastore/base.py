from typing import Protocol


class ModbusDataStore(Protocol):
    def get_holding_registers(self, address: int, count: int) -> list[int]:
        # TODO: Return count read/write 16-bit holding-register values starting at address.
        # TODO: Raise InvalidAddressError when the requested range is not mapped.
        ...

    def set_holding_registers(self, address: int, values: list[int]) -> None:
        # TODO: Write consecutive 16-bit holding-register values starting at address.
        # TODO: Validate addresses and values before mutating datastore state.
        ...

    def get_input_registers(self, address: int, count: int) -> list[int]:
        # TODO: Return count read-only 16-bit input-register values starting at address.
        # TODO: Raise InvalidAddressError when the requested range is not mapped.
        ...

    def get_coils(self, address: int, count: int) -> list[bool]:
        # TODO: Return count read/write coil bit values starting at address.
        # TODO: Raise InvalidAddressError when the requested range is not mapped.
        ...

    def set_coils(self, address: int, values: list[bool]) -> None:
        # TODO: Write consecutive coil bit values starting at address.
        # TODO: Validate addresses and boolean values before mutating datastore state.
        ...

    def get_discrete_inputs(self, address: int, count: int) -> list[bool]:
        # TODO: Return count read-only discrete-input bit values starting at address.
        # TODO: Raise InvalidAddressError when the requested range is not mapped.
        ...
