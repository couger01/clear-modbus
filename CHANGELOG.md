# Changelog

Release notes are managed with [Towncrier](https://towncrier.readthedocs.io/).

<!-- towncrier release notes start -->

## 0.1.1 (2026-06-07)

### Documentation

- Added task-oriented Sphinx guide pages for getting started, clients, server,
  simulator, datastore, protocol behavior, error handling, and release notes. ([#1](https://github.com/couger01/clear-modbus/issues/1))

### Miscellaneous

- Added interoperability fixture coverage for Modbus TCP and RTU request/response frames, including PDU dispatch, MBAP handling, RTU CRC validation, client execute paths, write echoes, and exception responses. ([#2](https://github.com/couger01/clear-modbus/issues/2))
- Added transport timeout and disconnect behavior tests for TCP and serial transports, including close failures, connection failures, write failures, partial writes, short reads, and timeout error mapping. ([#3](https://github.com/couger01/clear-modbus/issues/3))


## 0.1.0 (2026-06-07)

### Features

- Added Modbus TCP server support backed by an in-memory datastore.
- Added a local Modbus TCP simulator for tests and development workflows.
- Added protocol support for reading coils, reading discrete inputs, reading
  registers, writing single coils and registers, and writing multiple coils and
  registers.
- Added the initial async Modbus TCP and RTU client APIs.

### Documentation

- Added README examples for register writes, coil and discrete-input operations,
  and simulator background tasks.
- Added README usage examples and Sphinx API documentation.

### Miscellaneous

- Added a clean-environment wheel smoke test and made the source distribution
  test-exclusion policy explicit.
- Added packaging, test, lint, type-check, and documentation build configuration
  for the initial release.
