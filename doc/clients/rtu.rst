Modbus RTU Client
=================

Use :class:`clear_modbus.ModbusRtuClient` to communicate with Modbus RTU
devices over a serial connection. The client accepts:

* ``port``
* ``unit_id``
* ``baudrate``
* ``timeout``
* ``transport``

The ``transport`` parameter is mainly useful for providing a fake serial
connection in unit tests.

Read input registers with an async context manager:

.. code-block:: python

   import asyncio

   from clear_modbus import ModbusRtuClient


   async def main() -> None:
       async with ModbusRtuClient(
           port="/dev/ttyUSB0",
           unit_id=1,
           baudrate=9600,
           timeout=1.0,
       ) as client:
           response = await client.read_input_registers(address=0, count=2)
           print(response.values)


   asyncio.run(main())

Write operations use the same high-level method names as the TCP client:

.. code-block:: python

   single_register = await client.write_single_register(address=10, value=123)
   multiple_registers = await client.write_multiple_registers(
       address=20,
       values=[100, 200, 300],
   )
   read_after_write = await client.read_write_multiple_registers(
       read_address=0,
       read_count=2,
       write_address=20,
       values=[100, 200],
   )
   masked_register = await client.mask_write_register(
       address=30,
       and_mask=0x00F2,
       or_mask=0x0025,
   )
   single_coil = await client.write_single_coil(address=0, value=True)
   multiple_coils = await client.write_multiple_coils(
       address=1,
       values=[True, False, True],
   )

RTU support uses ``pyserial`` for serial communication and ``asyncio.to_thread``
to keep serial operations compatible with async callers. Serial port names vary
by platform. Windows commonly uses ``COM`` ports such as ``COM3``. Unix-like
systems commonly use device paths such as ``/dev/ttyUSB0`` or
``/dev/tty.usbserial-0001``.

RTU request handling works like this

* Create a request PDU.
* Add the unit id to the PDU.
* Append the RTU CRC.
* Use the serial transport to send and receive bytes.
* Validate and return the response.

Modbus RTU responses do not include a frame length field.
Therefore the client must determine the expected response size from the request type and first response bytes.

Read responses and read/write multiple-register responses use a byte-count field.
The response begins with

- unit id
- function code
- byte count

After reading that prefix, the client reads ``byte_count`` data bytes plus the two-byte CRC.

Write echo responses are fixed-size therefore write functions on server-side echo the function code, starting address and written value or quantity.
The responses are always 8 bytes total:

- unit id: 1 byte
- function code: 1 byte
- address: 2 bytes
- value or count: 2 bytes
- CRC: 2 bytes

Exception responses are also fixed-size at 5 bytes total:

- unit id: 1 byte
- exception function code: 1 byte
- exception code: 1 byte
- CRC: 2 bytes

API reference: :class:`clear_modbus.ModbusRtuClient`
