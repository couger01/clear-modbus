Error Handling
==============

clear-modbus groups package-specific failures under
:class:`clear_modbus.exceptions.ModbusError`. Catch ``ModbusError`` when an
application wants to handle any library-level Modbus failure. Catch specific
subclasses when the application can respond differently to transport,
protocol, or remote device errors.

Transport Errors
----------------

Transport errors are raised when bytes cannot be moved reliably:

* ``ModbusConnectionError`` for failed connections or disconnected transports.
* ``ModbusTimeoutError`` when connect, send, or receive operations exceed the
  configured timeout.
* ``ModbusTransportError`` for lower-level transport failures such as partial
  writes or short reads.

TCP and serial transports both expose ``connect()``, ``close()``, ``send()``,
and ``receive()`` methods. High-level clients surface transport exceptions from
those methods.

Protocol Errors
---------------

Protocol errors are raised when bytes or decoded responses do not satisfy the
Modbus protocol contract:

* ``ModbusFrameError`` for malformed TCP or RTU frames.
* ``ModbusCRCError`` for RTU CRC mismatches.
* ``ModbusPDUError`` for malformed or unsupported PDUs.
* ``ModbusResponseMismatchError`` when a response does not match the request
  context, transaction id, unit id, expected response type, or write echo.

High-level client helpers raise
``ModbusExceptionResponseError`` when a remote device returns a valid Modbus
exception response. They raise ``ModbusResponseMismatchError`` when the remote
response is not the response expected for the operation.

ValueError
----------

``ValueError`` is still used for invalid caller input, invalid local
configuration, and malformed low-level decode inputs. For example, an invalid
register count can raise ``ValueError`` before any bytes are sent. Datastore
construction can also raise ``ValueError`` when configured blocks overlap.

Datastore Errors
----------------

Datastore blocks raise datastore-specific exceptions:

* ``InvalidAddressError`` when a requested range is not mapped.
* ``InvalidValueError`` when a value has the wrong type or range.
* ``ReadOnlyDataBlockError`` when writing to a read-only block.

The TCP server maps these to Modbus exception responses instead of exposing the
Python exceptions to remote clients.

Example
-------

.. code-block:: python

   import asyncio

   from clear_modbus import ModbusExceptionResponseError, ModbusTcpClient
   from clear_modbus.exceptions import (
       ModbusResponseMismatchError,
       ModbusTimeoutError,
       ModbusTransportError,
   )

   async def main() -> None:
       async with ModbusTcpClient(host="127.0.0.1") as client:
           try:
               response = await client.read_holding_registers(address=0, count=2)
           except ModbusExceptionResponseError as exc:
               print("Device returned exception:", exc.exception_code)
           except ModbusResponseMismatchError:
               print("Device returned an unexpected response.")
           except ModbusTimeoutError:
               print("The request timed out.")
           except ModbusTransportError:
               print("The connection failed.")
           else:
               print(response.values)


   asyncio.run(main())

API reference: :mod:`clear_modbus.exceptions` and
:mod:`clear_modbus.datastore.errors`
