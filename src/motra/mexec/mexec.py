import logging
import shlex
import os
import sys

from pathlib import Path

from motra.common.capcon_protocol import GenericPayload

logger = logging.getLogger(__name__)


def mexec_run(payload_id: str):
    """
    Run a payload using a custom configuration we load from the current environment.

    The workspace is configured by the current client application and available through
    systemd. The main worker process is started inside the live environment of our client.
    We just need to find the correct json configuration for this payload and execute it.

    Alternatively the main process can get additional information from the env file,
    which was also loaded by sytemd at this point.
    """

    # get the current path, this sould be inside the live environment of client/server
    workspace = Path().resolve()
    print(f"payload_id: {payload_id}")
    print(f"logging files to {workspace}")

    target_payload = workspace / f"{payload_id}.json"
    configuration = None

    # load the current payload configuration
    if target_payload.exists() and target_payload.is_file():
        payload = target_payload.read_text()
        logger.info(f"Found existing payload configuration for {payload_id}")
        configuration = GenericPayload.model_validate_json(payload)
    else:
        raise RuntimeError(
            f"configuration for {payload_id} does not exist in {workspace}. "
        )

    # get capcon/payload.command
    # use shlex to parse the command string
    print(f"Executing: {configuration.command}")
    command = shlex.split(configuration.command)
    prog = command[0]

    # flush all logs to systemd, otherwise these will be lost
    sys.stdout.flush()

    # update the current process (call exec***)
    os.execvp(prog, command)


if __name__ == "__main__":
    mexec_run()
