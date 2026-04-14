import websockets
import logging
from websockets.exceptions import ConnectionClosed, InvalidHandshake

from motra.common.response_types import Response, Status
from motra.workspace.workspace_configuration import FileConfiguration

logger = logging.getLogger(__name__)


class ClientConnection:
    def __init__(self, app: FileConfiguration):
        """
        Configure and hold the runtime parameters for the client side websocket connection.
        """

        self.uri = app.configuration.server_uri
        self.websocket = None  # holds the websocket reference

        self.retries = 0
        self.retry_time = app.configuration.retry_time
        self.retry_limit = app.configuration.retry_limit

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
        except ConnectionClosed as e:
            logger.error(
                "Server closed the connection unexpectedly",
                exc_info=True,
            )
            return Response(status=Status.CONNECTION_CLOSED, payload=e.reason)

    async def receive(self):
        try:
            response = await self.websocket.recv()
            logger.debug("received message", extra={"data": response})
            return Response(status=Status.SUCCESS, payload=response)
        except ConnectionClosed as e:
            logger.error(
                "Server closed the connection unexpectedly",
                exc_info=True,
            )
            return Response(status=Status.CONNECTION_CLOSED, payload=e.reason)

    # @property
    def is_connected(self) -> bool:
        """A property to cleanly check the connection status."""
        return self.websocket is not None

    def backoff(self) -> int:
        """
        Returns the current backoff time for the client upon retry. In case the
        backofftime is below the backofflimit, the counter is incremented.
        Once the count reaches the backoff limit, exit will be called.
        """
        tick = self.retry_time

        if self.retries < self.retry_limit:
            self.retry_time += 2
            self.retries += 1
        else:
            # stop the client, if the server fails to respond
            # also usefull to kill some orphaned clients in case the disown fails
            logger.error("Reached configured retries, stopping the Client")
            exit(1)

        return tick
