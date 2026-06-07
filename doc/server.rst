Server
======

Use :class:`clear_modbus.server.ModbusTcpServer` to expose a datastore over
Modbus TCP. The server accepts TCP clients, decodes MBAP-framed requests, routes
supported PDUs to a datastore, and writes normal or exception response frames
back to the client.

Create a datastore and start a server with an async context manager:

.. code-block:: python

   import asyncio

   from clear_modbus.datastore import BitBlock, MemoryDataStore, RegisterBlock
   from clear_modbus.server import ModbusTcpServer


   async def main() -> None:
       datastore = MemoryDataStore(
           holding_registers=[
               RegisterBlock(start_address=0, values=[10, 20, 30]),
           ],
           coils=[
               BitBlock(start_address=0, values=[True, False, True]),
           ],
       )

       async with ModbusTcpServer(
           host="127.0.0.1",
           port=1502,
           datastore=datastore,
       ):
           await asyncio.Event().wait()


   asyncio.run(main())

Supported Function Codes
------------------------

The server supports these request types:

* ``ReadCoilsRequest`` -> ``datastore.get_coils()``
* ``ReadDiscreteInputsRequest`` -> ``datastore.get_discrete_inputs()``
* ``ReadHoldingRegistersRequest`` -> ``datastore.get_holding_registers()``
* ``ReadInputRegistersRequest`` -> ``datastore.get_input_registers()``
* ``WriteSingleCoilRequest`` -> ``datastore.set_coils()``
* ``WriteSingleRegisterRequest`` -> ``datastore.set_holding_registers()``
* ``WriteMultipleCoilsRequest`` -> ``datastore.set_coils()``
* ``WriteMultipleRegistersRequest`` -> ``datastore.set_holding_registers()``

Read requests return decoded values from the datastore. Write requests return
the Modbus echo response defined by the protocol: the function code, starting
address, and written value or quantity.

Exception Responses
-------------------

Datastore and protocol failures are mapped to Modbus exception responses:

* Unsupported request types return ``ILLEGAL_FUNCTION``.
* Invalid or unmapped datastore ranges return ``ILLEGAL_DATA_ADDRESS``.
* Writes to read-only blocks return ``ILLEGAL_DATA_ADDRESS``.
* Invalid datastore values return ``ILLEGAL_DATA_VALUE``.
* Malformed PDU bytes handled by the client loop return ``ILLEGAL_FUNCTION`` or
  ``ILLEGAL_DATA_VALUE`` depending on the decode failure.

Lifecycle
---------

``start()`` binds the TCP socket and begins accepting clients. Calling
``start()`` again while the server is running is harmless. ``stop()`` closes the
server socket and waits for it to finish closing. Prefer ``async with`` for most
applications so ``stop()`` is called even when the surrounding task exits with
an exception.

Current Limitations
-------------------

The server implementation is TCP-only. RTU support currently exists on the
client side, but there is no RTU server implementation. The server also uses one
datastore for all unit ids; applications that need per-unit datastore routing
should wrap or extend the server behavior.

API reference: :class:`clear_modbus.server.ModbusTcpServer`
