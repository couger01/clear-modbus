"""Shared high-level operations for Modbus clients."""

from clear_modbus.exceptions import ModbusExceptionResponseError
from clear_modbus.protocol.pdu import (
    ExceptionResponse,
    ReadBitsResponse,
    ReadCoilsRequest,
    ReadDiscreteInputsRequest,
    ReadHoldingRegistersRequest,
    ReadInputRegistersRequest,
    ReadRegistersResponse,
    RequestPDU,
    ResponsePDU,
    WriteMultipleCoilsRequest,
    WriteMultipleCoilsResponse,
    WriteMultipleRegistersRequest,
    WriteMultipleRegistersResponse,
    WriteSingleCoilRequest,
    WriteSingleCoilResponse,
    WriteSingleRegisterRequest,
    WriteSingleRegisterResponse,
)


def raise_for_exception_response(response: ResponsePDU) -> None:
    """Raise a public exception for a Modbus exception response.

    Parameters
    ----------
    response : ResponsePDU
        Decoded response PDU.

    Raises
    ------
    ModbusExceptionResponseError
        If ``response`` is an exception response PDU.

    """
    if isinstance(response, ExceptionResponse):
        raise ModbusExceptionResponseError(
            function_code=response.function_code,
            exception_code=response.exception_code,
        )


class ModbusClientOperations:
    """High-level Modbus operations shared by TCP and RTU clients."""

    async def execute(
        self,
        request: RequestPDU,
        unit_id: int | None = None,
    ) -> ResponsePDU:
        """Send a request and return the decoded response.

        Parameters
        ----------
        request : RequestPDU
            Request PDU to send.
        unit_id : int | None
            Unit identifier override.

        Returns
        -------
        ResponsePDU
            Decoded response PDU.

        Raises
        ------
        NotImplementedError
            If a concrete client does not implement this method.

        """
        raise NotImplementedError

    async def read_coils(
        self,
        address: int,
        count: int,
        unit_id: int | None = None,
    ) -> ReadBitsResponse:
        """Read coil values.

        Parameters
        ----------
        address : int
            First coil address.
        count : int
            Number of coils to read.
        unit_id : int | None
            Unit identifier override.

        Returns
        -------
        ReadBitsResponse
            Decoded coil values.

        Raises
        ------
        ValueError
            If the decoded response is not a read-bits response.

        """
        request = ReadCoilsRequest(address=address, count=count)
        response = await self.execute(request, unit_id=unit_id)
        raise_for_exception_response(response)
        if not isinstance(response, ReadBitsResponse):
            raise ValueError()
        return response

    async def read_discrete_inputs(
        self,
        address: int,
        count: int,
        unit_id: int | None = None,
    ) -> ReadBitsResponse:
        """Read discrete-input values.

        Parameters
        ----------
        address : int
            First discrete-input address.
        count : int
            Number of inputs to read.
        unit_id : int | None
            Unit identifier override.

        Returns
        -------
        ReadBitsResponse
            Decoded discrete-input values.

        Raises
        ------
        ValueError
            If the decoded response is not a read-bits response.

        """
        request = ReadDiscreteInputsRequest(address=address, count=count)
        response = await self.execute(request, unit_id=unit_id)
        raise_for_exception_response(response)
        if not isinstance(response, ReadBitsResponse):
            raise ValueError()
        return response

    async def read_holding_registers(
        self,
        address: int,
        count: int,
        unit_id: int | None = None,
    ) -> ReadRegistersResponse:
        """Read holding-register values.

        Parameters
        ----------
        address : int
            First holding-register address.
        count : int
            Number of registers to read.
        unit_id : int | None
            Unit identifier override.

        Returns
        -------
        ReadRegistersResponse
            Decoded holding-register values.

        Raises
        ------
        ValueError
            If the decoded response is not a read-registers response.

        """
        request = ReadHoldingRegistersRequest(address=address, count=count)
        response = await self.execute(request, unit_id=unit_id)
        raise_for_exception_response(response)
        if not isinstance(response, ReadRegistersResponse):
            raise ValueError()
        return response

    async def read_input_registers(
        self,
        address: int,
        count: int,
        unit_id: int | None = None,
    ) -> ReadRegistersResponse:
        """Read input-register values.

        Parameters
        ----------
        address : int
            First input-register address.
        count : int
            Number of registers to read.
        unit_id : int | None
            Unit identifier override.

        Returns
        -------
        ReadRegistersResponse
            Decoded input-register values.

        Raises
        ------
        ValueError
            If the decoded response is not a read-registers response.

        """
        request = ReadInputRegistersRequest(address=address, count=count)
        response = await self.execute(request, unit_id=unit_id)
        raise_for_exception_response(response)
        if not isinstance(response, ReadRegistersResponse):
            raise ValueError()
        return response

    async def write_single_register(
        self,
        address: int,
        value: int,
        unit_id: int | None = None,
    ) -> WriteSingleRegisterResponse:
        """Write one holding-register value.

        Parameters
        ----------
        address : int
            Register address to write.
        value : int
            Register value to write.
        unit_id : int | None
            Unit identifier override.

        Returns
        -------
        WriteSingleRegisterResponse
            Decoded write echo response.

        Raises
        ------
        ValueError
            If the decoded response type or echoed address/value is invalid.

        """
        request = WriteSingleRegisterRequest(address=address, value=value)
        response = await self.execute(request, unit_id=unit_id)
        raise_for_exception_response(response)
        if not isinstance(response, WriteSingleRegisterResponse):
            raise ValueError()
        if response.address != address:
            raise ValueError()
        if response.value != value:
            raise ValueError()
        return response

    async def write_single_coil(
        self,
        address: int,
        value: bool,
        unit_id: int | None = None,
    ) -> WriteSingleCoilResponse:
        """Write one coil value.

        Parameters
        ----------
        address : int
            Coil address to write.
        value : bool
            Coil value to write.
        unit_id : int | None
            Unit identifier override.

        Returns
        -------
        WriteSingleCoilResponse
            Decoded write echo response.

        Raises
        ------
        ValueError
            If the decoded response type or echoed address/value is invalid.

        """
        request = WriteSingleCoilRequest(address=address, value=value)
        response = await self.execute(request, unit_id=unit_id)
        raise_for_exception_response(response)
        if not isinstance(response, WriteSingleCoilResponse):
            raise ValueError()
        if response.address != address:
            raise ValueError()
        if response.value != value:
            raise ValueError()
        return response

    async def write_multiple_registers(
        self,
        address: int,
        values: list[int],
        unit_id: int | None = None,
    ) -> WriteMultipleRegistersResponse:
        """Write multiple holding-register values.

        Parameters
        ----------
        address : int
            First register address to write.
        values : list[int]
            Register values to write.
        unit_id : int | None
            Unit identifier override.

        Returns
        -------
        WriteMultipleRegistersResponse
            Decoded write echo response.

        Raises
        ------
        ValueError
            If the decoded response type or echoed address/count is invalid.

        """
        request = WriteMultipleRegistersRequest(address=address, values=values)
        response = await self.execute(request, unit_id=unit_id)
        raise_for_exception_response(response)
        if not isinstance(response, WriteMultipleRegistersResponse):
            raise ValueError()
        if response.address != address:
            raise ValueError()
        if response.count != len(values):
            raise ValueError()
        return response

    async def write_multiple_coils(
        self,
        address: int,
        values: list[bool],
        unit_id: int | None = None,
    ) -> WriteMultipleCoilsResponse:
        """Write multiple coil values.

        Parameters
        ----------
        address : int
            First coil address to write.
        values : list[bool]
            Coil values to write.
        unit_id : int | None
            Unit identifier override.

        Returns
        -------
        WriteMultipleCoilsResponse
            Decoded write echo response.

        Raises
        ------
        ValueError
            If the decoded response type or echoed address/count is invalid.

        """
        request = WriteMultipleCoilsRequest(address=address, values=values)
        response = await self.execute(request, unit_id=unit_id)
        raise_for_exception_response(response)
        if not isinstance(response, WriteMultipleCoilsResponse):
            raise ValueError()
        if response.address != address:
            raise ValueError()
        if response.count != len(values):
            raise ValueError()
        return response
