from typing import Protocol


class Transport(Protocol):
    async def connect(self) -> None:
        # TODO: Open the underlying connection resource.
        ...

    async def close(self) -> None:
        # TODO: Close the underlying connection resource idempotently.
        ...

    async def send(self, data: bytes) -> None:
        # TODO: Write all bytes to the connection or raise a transport error.
        ...

    async def receive(self, size: int) -> bytes:
        # TODO: Read exactly size bytes or raise timeout/connection errors.
        ...
