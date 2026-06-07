Protocol
========

The protocol package contains the PDU, TCP frame, RTU frame, and codec helpers
used by clients and servers.

Supported Function Codes
------------------------

clear-modbus currently supports these standard function codes:

========================== ====== ====================================== =====================================
Function                   Code   Request class                          Response class
========================== ====== ====================================== =====================================
Read coils                 0x01   ``ReadCoilsRequest``                   ``ReadBitsResponse``
Read discrete inputs       0x02   ``ReadDiscreteInputsRequest``          ``ReadBitsResponse``
Read holding registers     0x03   ``ReadHoldingRegistersRequest``        ``ReadRegistersResponse``
Read input registers       0x04   ``ReadInputRegistersRequest``          ``ReadRegistersResponse``
Write single coil          0x05   ``WriteSingleCoilRequest``             ``WriteSingleCoilResponse``
Write single register      0x06   ``WriteSingleRegisterRequest``         ``WriteSingleRegisterResponse``
Write multiple coils       0x0F   ``WriteMultipleCoilsRequest``          ``WriteMultipleCoilsResponse``
Write multiple registers   0x10   ``WriteMultipleRegistersRequest``      ``WriteMultipleRegistersResponse``
========================== ====== ====================================== =====================================

PDU Layer
---------

The PDU layer handles function-code payloads independent of the transport.
Request classes encode function code and request payload bytes. Response
classes decode function-specific response payloads. Response dispatch uses the
original request as context so the same response shape can be interpreted
correctly for similar functions, such as holding-register reads and
input-register reads.

``decode_request_pdu()`` is used by the server to turn raw PDU bytes into a
request object. ``decode_response_pdu()`` is used by clients to decode a
response in the context of the request that was sent.

Modbus TCP Framing
------------------

Modbus TCP wraps the PDU in an MBAP header. The MBAP header contains:

* transaction id
* protocol id
* length
* unit id

The MBAP ``length`` field includes the unit id plus the PDU length. TCP clients
can therefore read the fixed seven-byte MBAP header first, then read
``length - 1`` bytes for the PDU.

Modbus RTU Framing
------------------

Modbus RTU wraps the PDU with a unit id prefix and a two-byte CRC suffix. The
CRC is encoded little-endian, as required by Modbus RTU:

.. code-block:: text

   unit id | function code + payload | CRC low byte | CRC high byte

RTU does not include a frame-level length field, so RTU clients determine the
expected response size from the request type and response prefix.

Exception Responses
-------------------

A Modbus exception response sets the high bit on the function code. For
example, an exception response for function ``0x03`` uses function code
``0x83``. The library provides helpers to identify exception function codes,
strip the exception bit, and add the exception bit.

Decoded ``ExceptionResponse`` objects store the original function code with the
exception bit stripped plus the Modbus exception code.

Validation Boundaries
---------------------

Invalid caller input, invalid local configuration, and malformed low-level
decode inputs raise ``ValueError`` in the relevant constructors or decoders.
Protocol-level mismatches discovered while matching a response to a request
raise package protocol exceptions such as ``ModbusResponseMismatchError``.

API reference: :mod:`clear_modbus.protocol.pdu`,
:mod:`clear_modbus.protocol.mbap`, :mod:`clear_modbus.protocol.rtu`,
:mod:`clear_modbus.protocol.codec`, and :mod:`clear_modbus.protocol.functions`
