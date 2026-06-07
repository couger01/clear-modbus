clear-modbus documentation
==========================

clear-modbus is an async Python toolkit for Modbus TCP, Modbus RTU, server
workflows, and local simulation.

Use the user guide for task-oriented examples and the API reference for exact
class, method, and protocol helper details. The project is organized around a
small set of composable pieces: clients for application code, a TCP server and
datastore for exposing values, protocol helpers for frames and PDUs, and a
simulator for tests and local development.

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   getting-started
   clients/index
   server
   simulator
   datastore
   protocol
   errors

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api
   release-notes
