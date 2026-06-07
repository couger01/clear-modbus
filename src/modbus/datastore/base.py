"""Protocol for Modbus datastore implementations."""

from typing import Protocol


class ModbusDataStore(Protocol):
    """Read and write Modbus data areas by address range."""

    def get_holding_registers(self, address: int, count: int) -> list[int]:
        """Return read/write holding-register values.

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
        ...

    def set_holding_registers(self, address: int, values: list[int]) -> None:
        """Write holding-register values.

        Parameters
        ----------
        address : int
            First holding-register address.
        values : list[int]
            Register values to write.

        """
        ...

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
        ...

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
        ...

    def set_coils(self, address: int, values: list[bool]) -> None:
        """Write coil values.

        Parameters
        ----------
        address : int
            First coil address.
        values : list[bool]
            Coil values to write.

        """
        ...

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
        ...
