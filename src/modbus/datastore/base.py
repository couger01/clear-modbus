from typing import Protocol


class ModbusDataStore(Protocol):
    def get_holding_registers(self, address: int, count: int) -> list[int]:
        """Return read/write 16-bit holding-register values for the requested range."""
        ...

    def set_holding_registers(self, address: int, values: list[int]) -> None:
        """Write consecutive 16-bit holding-register values starting at address."""
        ...

    def get_input_registers(self, address: int, count: int) -> list[int]:
        """Return read-only 16-bit input-register values for the requested range."""
        ...

    def get_coils(self, address: int, count: int) -> list[bool]:
        """Return read/write coil bit values for the requested range."""
        ...

    def set_coils(self, address: int, values: list[bool]) -> None:
        """Write consecutive coil bit values starting at address."""
        ...

    def get_discrete_inputs(self, address: int, count: int) -> list[bool]:
        """Return read-only discrete-input bit values for the requested range."""
        ...
