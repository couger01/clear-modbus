Clients
=======

clear-modbus provides shared high-level operations for TCP and RTU clients.

The :class:`clear_modbus.ModbusTcpClient` and
:class:`clear_modbus.ModbusRtuClient` classes share read/write helper methods
through the ``ModbusClientOperations`` mixin.

Supported high-level operations:

* ``read_coils``
* ``read_discrete_inputs``
* ``read_holding_registers``
* ``read_input_registers``
* ``write_single_coil``
* ``write_single_register``
* ``write_multiple_coils``
* ``write_multiple_registers``

Prefer the high-level read/write methods for normal application code. Use
``execute()`` directly when you need lower-level PDU access or future custom
function-code support.

See :doc:`Error Handling <../errors>` for exception response and response
mismatch behavior.

.. toctree::
   :maxdepth: 1

   tcp
   rtu
