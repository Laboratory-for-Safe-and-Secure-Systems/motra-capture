import typer
from typing_extensions import Annotated

from motra.client.client_connection import ClientConnection
from motra.logging.client_config import (
    client_defaultConsoleLogger,
    client_defaultFileLogger,
)
from motra.workspace.workspace import (
    create_entity_workspace,
    open_existing_workspace,
)


client_cli = typer.Typer(no_args_is_help=True)


@client_cli.command()
def client(
    client_id: Annotated[
        str,
        typer.Option(help="The custom name (or entity) for a client instance."),
    ] = "client",
    loglevel: Annotated[
        str,
        typer.Option(help="Update the default logging level. <debug, info, warning>"),
    ] = "info",
):
    """
    Start a Client for generating test data for a device.
    """

    client_defaultConsoleLogger(loglevel)

    # we check the current environment for an active workspace
    # if we got a valid/explicit workspace dir, we use this as an override
    path, config = open_existing_workspace(client_id)
    if path is None:
        raise ValueError(
            "Could not access workspace. Is the default workspace configured?"
            "Check logs or run motra workspace client!"
        )

    filelog = path / f"{client_id}.log"
    client_defaultFileLogger(loglevel, filelog)

    from motra.client.measurement_client import MeasurementClient
    from motra.client.configuration import MotraClientConfig

    clientConfig = config.configuration
    conf = MotraClientConfig(
        retry_limit=clientConfig.retry_limit,
        retry_time=clientConfig.retry_time,
        workspace_root=config.data_storage,  # logs, data etc need to go into the subfolder
        ClientId=client_id,
    )

    # configure settings and storage local to this client
    connection = ClientConnection(clientConfig.server_uri)
    clientWorkspace = {
        "live": config.data_storage / "live",
        "staging": config.data_storage / "staging",
        "archived": config.data_storage / "archived",
    }

    create_entity_workspace(clientWorkspace)
    client = MeasurementClient(
        conf,
        connection,
        clientWorkspace,
    )

    try:
        # run the default state machine
        client.connect()
    except KeyboardInterrupt:
        print("\nSession stopped by user...")

    except RuntimeError as e:
        print(f"Stopping on error: {e}")
