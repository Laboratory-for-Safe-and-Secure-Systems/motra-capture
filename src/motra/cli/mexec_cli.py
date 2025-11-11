import typer
from typing_extensions import Annotated

from motra.mexec.mexec import mexec_run


mexec_cli = typer.Typer(no_args_is_help=True)


@mexec_cli.command()
def mexec(
    payload_id: Annotated[
        str,
        typer.Argument(help="The payload ID for the current run."),
    ],
):
    """
    Execute a capcon payload using the configured environment
    """

    mexec_run(payload_id)
