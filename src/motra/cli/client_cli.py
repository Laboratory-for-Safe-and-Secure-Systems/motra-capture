import typer
from typing_extensions import Annotated

from motra.client.client_connection import ClientConnection
from motra.logging.client_config import (
    client_defaultConsoleLogger,
    client_defaultFileLogger,
)
from motra.workspace.workspace import open_existing_workspace


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
    path, app = open_existing_workspace(client_id)
    if path is None:
        raise ValueError(
            "Could not access workspace. Is the default workspace configured?"
            "Check logs or run motra workspace client!"
        )

    filelog = path / f"{client_id}.log"
    client_defaultFileLogger(loglevel, filelog)

    from motra.client.measurement_client import MeasurementClient
    from motra.client.configuration import MotraClientConfig

    # configure runtime settings for this client
    connection = ClientConnection(app)
    clientWorkspace = {
        "live": app.configuration.live_workspace,
        "staging": app.configuration.staging_workspace,
        "archive": app.configuration.archive_workspace,
    }

    client = MeasurementClient(
        entity=app.entity_id,
        clientConnection=connection,
        workspace=clientWorkspace,
    )

    try:
        # run the default state machine
        client.connect()
    except KeyboardInterrupt:
        typer.secho("\nSession stopped by user...", fg=typer.colors.YELLOW)

    except RuntimeError as e:
        typer.secho(f"Stopping on error: {e}", fg=typer.colors.RED)
