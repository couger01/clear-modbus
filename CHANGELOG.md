# Changelog

Release notes are managed with [Towncrier](https://towncrier.readthedocs.io/).

<!-- towncrier release notes start -->

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
