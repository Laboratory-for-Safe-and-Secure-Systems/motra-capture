from pathlib import Path
import logging


# this would be the module specific logger
main_log = logging.getLogger(__name__)


class MotraClientConfig:

    retrytime: int
    retrylimit: int

    def __init__(
        self,
        retry_time: int,
        retry_limit: int,
        workspace_root: Path,
        ClientId: str,
    ):
        """Internal configuration and state for the websocket client"""

        self.retrytime = retry_time
        self.retrylimit = retry_limit
        self.retries = 0
        self.workspace_root = workspace_root
        self.ClientId = ClientId

    def backoff(self) -> int:
        """
        Returns the current backoff time for the client upon retry. In case the
        backofftime is below the backofflimit, the counter is incremented.
        Once the count reaches the backoff limit, exit will be called.
        """
        tick = self.retrytime

        if self.retries < self.retrylimit:
            self.retrytime += 2
            self.retries += 1
        else:
            # stop the client, if the server fails to respond
            # also usefull to kill some orphaned clients in case the disown fails
            main_log.error("Reached configured retries, stopping the Client")
            exit(1)

        return tick
