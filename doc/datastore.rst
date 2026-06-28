Datastore
=========

The datastore layer stores Modbus data in contiguous blocks. Register data uses
:class:`clear_modbus.datastore.RegisterBlock`; bit data uses
:class:`clear_modbus.datastore.BitBlock`; and
:class:`clear_modbus.datastore.MemoryDataStore` routes reads and writes to the
matching block for each Modbus data area.

Register Blocks
---------------

``RegisterBlock`` represents a contiguous range of 16-bit register values. The
``start_address`` is the first Modbus address in the block. ``end_address`` is
inclusive and is derived from ``start_address`` plus the number of values.

Reads return a copy of the requested values. Writes update the backing list in
place after validating that every value is an ``int`` between ``0`` and
``0xFFFF``. Read-only blocks reject writes with
``ReadOnlyDataBlockError``.

.. code-block:: python

   from clear_modbus.datastore import RegisterBlock

   block = RegisterBlock(start_address=100, values=[10, 20, 30])

   assert block.end_address == 102
   assert block.read(address=101, count=2) == [20, 30]

   block.write(address=101, values=[55, 66])
   assert block.values == [10, 55, 66]

Bit Blocks
----------

``BitBlock`` represents a contiguous range of boolean values for coils or
discrete inputs. It has the same address-range behavior as ``RegisterBlock``,
but writes require values whose exact type is ``bool``.

.. code-block:: python

   from clear_modbus.datastore import BitBlock

   block = BitBlock(start_address=0, values=[True, False, True])

   assert block.end_address == 2
   assert block.read(address=1, count=2) == [False, True]

   block.write(address=1, values=[True, True])
   assert block.values == [True, True, True]

Memory Datastore
----------------

``MemoryDataStore`` has four data areas:

* ``holding_registers`` for read/write register data.
* ``input_registers`` for read-only register-style data.
* ``coils`` for read/write bit data.
* ``discrete_inputs`` for read-only bit-style data.

The datastore sorts each data area by block start address during construction
and stores the block collections as immutable tuples. Add, remove, or reorder
blocks by constructing a new datastore. Block values remain mutable through the
datastore write methods and the block ``write`` methods.

The datastore rejects overlapping non-empty blocks inside the same data area.
For a read or write, one block must contain the full requested range. Requests
do not span multiple blocks, even when adjacent blocks together cover the full
range.

.. code-block:: python

   from clear_modbus.datastore import BitBlock, MemoryDataStore, RegisterBlock

   datastore = MemoryDataStore(
       holding_registers=[
           RegisterBlock(start_address=0, values=[10, 20]),
       ],
       input_registers=[
           RegisterBlock(start_address=100, values=[30, 40], readonly=True),
       ],
       coils=[
           BitBlock(start_address=0, values=[True, False]),
       ],
       discrete_inputs=[
           BitBlock(start_address=100, values=[False, True], readonly=True),
       ],
   )

   assert datastore.get_holding_registers(address=0, count=2) == [10, 20]
   datastore.set_holding_registers(address=0, values=[11, 22])

   assert isinstance(datastore.holding_registers, tuple)

Errors
------

Datastore operations raise ``InvalidAddressError`` when no block contains the
requested range, ``InvalidValueError`` when a value has the wrong type or range,
and ``ReadOnlyDataBlockError`` when writing to a read-only block. The TCP server
maps these datastore errors to Modbus exception responses.
