import typer
import motra.cli.workspace_cli as workspace
import motra.cli.client_cli as client
import motra.cli.server_cli as server
import motra.cli.capcon_cli as capcon
import motra.cli.mexec_cli as mexec

# Create the Typer application
motra_cli = typer.Typer(no_args_is_help=True)


# add the workspace subcommands
helptext = "Workspace configuration for setting up the systemd scheduler."
motra_cli.add_typer(workspace.workspace_cli, name="workspace", help=helptext)

motra_cli.add_typer(client.client_cli)

motra_cli.add_typer(server.server_cli)

motra_cli.add_typer(capcon.capcon_cli)

motra_cli.add_typer(mexec.mexec_cli)


if __name__ == "__main__":
    motra_cli()
