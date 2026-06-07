"""Transport protocol shared by client implementations."""

from typing import Protocol


class Transport(Protocol):
    """Asynchronous byte transport used by Modbus clients."""

    async def connect(self) -> None:
        """Open the underlying connection resource."""
        ...

    async def close(self) -> None:
        """Close the underlying connection resource idempotently."""
        ...

    async def send(self, data: bytes) -> None:
        """Write all bytes to the connection or raise a transport error."""
        ...

    async def receive(self, size: int) -> bytes:
        """Read exactly size bytes or raise timeout/connection errors."""
        ...
