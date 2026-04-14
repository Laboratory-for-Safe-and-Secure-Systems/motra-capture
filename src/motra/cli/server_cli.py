import typer
import logging
from typing_extensions import Annotated

from motra.logging.server_config import (
    server_defaultConsoleLogger,
    server_defaultFileLogger,
)
from motra.workspace.workspace import (
    create_entity_workspace,
    init_entity_workspace_dir,
)


server_cli = typer.Typer(no_args_is_help=True)


@server_cli.command()
def server(
    loglevel: Annotated[
        str,
        typer.Option(help="Update the default logging level."),
    ] = "Info",
    reload: Annotated[
        bool,
        typer.Option(
            help="Enables uvicorn reload for changes to the configuration options."
        ),
    ] = False,
):
    """
    Run a local measurement server to orchestrate a testbed.
    """
    # we check the current environment for an active workspace
    # if we got a valid/explicit workspace dir, we use this as an override
    # create a new ServerConfig globally and initialize the structure for FastAPI

    server_defaultConsoleLogger(loglevel)

    # try to load the workspace, so we can put our logs there
    workspace, app = init_entity_workspace_dir(None, "server")
    if workspace is None:
        raise ValueError("Could not access workspace. Check logs!")

    filelog = workspace / "server.log"
    server_defaultFileLogger("debug", filelog)

    from motra.server.server import run
    from motra.server.configuration import MotraServerConfig, set_server_config

    log = logging.getLogger("__name__")

    # so we found existing configuration
    if app:
        log.info(f"Found existing configuration at {workspace}")

    # we need to update the central configuraiton for FastAPs

    config = MotraServerConfig(app)
    set_server_config(config)

    level = getattr(logging, loglevel.upper())

    run(
        reload=reload,
        loglevel=level,
        port=app.configuration.port,
        host=app.configuration.host,
    )
