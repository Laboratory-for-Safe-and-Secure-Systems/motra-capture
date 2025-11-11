import websockets
import logging
from websockets.exceptions import ConnectionClosed, InvalidHandshake

from motra.common.response_types import Response, Status

logger = logging.getLogger(__name__)


class ClientConnection:
    def __init__(self, uri):
        """Configure the default logger for the Client."""

        self.uri = uri
        self.websocket = None  # holds the websocket reference

    def set_socket(self, socket: websockets):
        self.websocket = socket

    def get_socket(self) -> websockets:
        return self.websocket

    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.uri)
        except InvalidHandshake:
            logger.error(
                "Failed to initialize connection to server. Is the fastAPI server running?",
                exc_info=True,
            )
            return Response(status=Status.CONNECTION_FAILED)

        except OSError:
            logger.error(
                "Multiple Exceptions upon Connect, is the Server running? Check logs!",
                exc_info=True,
            )
            return Response(status=Status.ERROR)

        return Response(status=Status.SUCCESS, data=self.websocket)

    async def disconnect(self, code: int = 1000, reason: str = ""):
        await self.websocket.close(code, reason)
        self.websocket = None
        return self.websocket

    async def send(self, data: str):
        try:
            logger.debug("sending message", extra={"data": data})
            await self.websocket.send(data)
        except ConnectionClosed:
            logger.error(
                "Server closed the connection unexpectedly",
                exc_info=True,
            )
            return Response(status=Status.CONNECTION_CLOSED)

    async def receive(self):
        try:
            response = await self.websocket.recv()
            logger.debug("received message", extra={"data": response})
            return Response(status=Status.SUCCESS, payload=response)
        except ConnectionClosed:
            logger.error(
                "Server closed the connection unexpectedly",
                exc_info=True,
            )
            return Response(status=Status.CONNECTION_CLOSED, data=None)

    # @property
    def is_connected(self) -> bool:
        """A property to cleanly check the connection status."""
        return self.websocket is not None
