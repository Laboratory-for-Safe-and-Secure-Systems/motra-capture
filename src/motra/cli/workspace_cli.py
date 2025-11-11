import json, sh, os, tempfile, typer, click, rich
from rich.json import JSON
from typing_extensions import Annotated

from motra.cli.choices import SchedulingModes

from motra.common.exec_environment import (
    get_current_python_path,
    run_privileged_command,
)
from motra.workspace.systemd_unit_generator import (
    motra_capture_unit,
    motra_client_unit,
    motra_mexec_unit,
    motra_server_unit,
    write_unit_to_disk,
)
from motra.workspace.workspace import (
    get_initialized_default_workspace,
    init_entity_datastorage,
    init_entity_workspace_dir,
    open_existing_workspace,
)
from motra.workspace.workspace_configuration import (
    ClientFileConfiguration,
    FileConfiguration,
    ServerFileConfiguration,
)

from motra.workspace.environment import environment_serialized


workspace_cli = typer.Typer(no_args_is_help=True)


@workspace_cli.command()
def client(
    server_uri: Annotated[
        str, typer.Option(prompt="Target URI to connect to")
    ] = "ws://localhost:12400/motra",
    retry_time: Annotated[str, typer.Option(prompt="Initial time for retry in s")] = 1,
    retry_limit: Annotated[
        str, typer.Option(prompt="No of times the client should retry a connection")
    ] = 3,
    scheduling_mode: Annotated[
        str,
        typer.Option(
            prompt="How the client should restart",
            click_type=click.Choice([e.value for e in SchedulingModes]),
            show_choices=True,
        ),
    ] = "systemd",
    entity: Annotated[
        str, typer.Option(prompt="The name of the new Client (Client ID)")
    ] = "client",
):
    """
    Create a workspacesconfiguration for a MOTRA client
    """
    print("Generating a new CLIENT configuration ...")

    # this will get the default or fallback directory for workspaces
    default_workspace_path, existingconf = init_entity_workspace_dir(None, entity)
    entity_storage = default_workspace_path / entity
    init_entity_datastorage(entity_storage)

    print(f"Selected workspace: {default_workspace_path}")

    env_setting = {
        "MOTRA_WORKSPACE": str(default_workspace_path),
        f"MOTRA_{entity.upper()}_WORKSPACE": str(
            default_workspace_path / f"{entity}.config"
        ),
    }

    # generate a default config
    clientconfig = ClientFileConfiguration(
        type="client",
        server_uri=server_uri,
        retry_time=retry_time,
        retry_limit=retry_limit,
        scheduling_mode=scheduling_mode,
    )

    appconfig = FileConfiguration(
        config_name=entity,
        configuration=clientconfig,
        environment=env_setting,
        data_storage=entity_storage,
    )

    # dump current configuration somewhere
    print("Generated workspace configuration: ")
    rich.print(JSON(appconfig.model_dump_json()))
    typer.confirm("Is the current configuration correct?", abort=True)

    # find currenty exported workspace (either by env or by fallback/user session)
    if existingconf:
        # we need to warn before overriding later on
        print(
            f"Checking existing data. Found existing CLIENT workspace"
            f"in {default_workspace_path}"
        )
        rich.print(JSON(existingconf.model_dump_json()))
        typer.confirm("Override existing configuration?", abort=True)

    # store configuration to disk
    print("Writing files to disk ")
    filestream = appconfig.model_dump_json(indent=2)
    config_path = default_workspace_path / f"{entity}.config"
    config_path.write_text(filestream)

    env_path = default_workspace_path / f"{entity}.env"
    env_path.write_text(environment_serialized(env_setting))

    # setup  systemd templates for the generated confguration
    python_exec = get_current_python_path() / "python3"
    command = f"{python_exec} -m motra.cli.cli client"
    environment_file = env_path
    working_dir = entity_storage

    # create the client template unit
    client_unit_file = motra_client_unit(
        os.getuid(),
        os.getgid(),
        command,
        environment_file,
        working_dir,
    )
    write_unit_to_disk(client_unit_file, "motra-client@.service")

    # TODO, this needs to be fixed; storage is not maintained here atm.
    working_dir = entity_storage / "live"

    # create the measurement unit
    capture_unit_file = motra_mexec_unit(
        "root",
        "root",
        python_exec,
        environment_file,
        working_dir,
    )
    write_unit_to_disk(capture_unit_file, "motra-client-mexec@.service")

    # update systemd
    command = ["systemctl", "daemon-reload"]
    run_privileged_command(command)


@workspace_cli.command()
def server(
    host: Annotated[
        str, typer.Option(prompt="Which IP/host should be used for the server: ")
    ] = "0.0.0.0",
    port: Annotated[int, typer.Option(prompt="Set the default port: ")] = 12400,
):
    """
    Create a workspace configuration for a MOTRA server
    """
    print("Generating a new SERVER configuration ...")

    # this will get the default or fallback directory for workspaces
    default_workspace_path, existingconf = init_entity_workspace_dir(None, "server")
    entity_storage = default_workspace_path / "server"
    init_entity_datastorage(entity_storage)
    print(f"Selected workspace: {default_workspace_path}")

    env_setting = {
        "MOTRA_WORKSPACE": str(default_workspace_path),
        "MOTRA_SERVER_WORKSPACE": str(default_workspace_path / "server.config"),
    }

    # generate a default config
    serverconfig = ServerFileConfiguration(
        type="server",
        port=port,
        host=host,
        # test_storage=None,
    )

    appconfig = FileConfiguration(
        config_name="server-default",
        configuration=serverconfig,
        environment=env_setting,
        data_storage=entity_storage,
    )

    # dump current configuration somewhere
    print("Generated workspace configuration: ")
    rich.print(JSON(appconfig.model_dump_json()))
    typer.confirm("Is the current configuration correct?", abort=True)

    # find currenty exported workspace (either by env or by fallback/user session)
    if existingconf:
        # we need to warn before overriding later on
        print(
            f"Checking existing data. Found existing SERVER workspace "
            f"in {default_workspace_path}"
        )
        rich.print(JSON(existingconf.model_dump_json()))
        typer.confirm("Override existing configuration?", abort=True)

    # store configuration to disk
    print("Writing files to disk ")
    filestream = appconfig.model_dump_json(indent=2)
    config_path = default_workspace_path / "server.config"
    config_path.write_text(filestream)

    env_path = default_workspace_path / "server.env"
    env_path.write_text(environment_serialized(env_setting))

    # setup  systemd templates for the generated confguration
    user = "root"
    group = "root"
    # command = "/home/las3/.cache/pypoetry/virtualenvs/motra-1JdFvEbk-py3.11/bin/python3 -m fastapi run server.py"  # this needs to be changed to motra-exec in the future
    python_exec = get_current_python_path() / "python3"
    command = f"{python_exec} -m motra.cli.cli server"
    environment_file = env_path
    working_dir = entity_storage

    server_unit_file = motra_server_unit(
        user,
        group,
        command,
        environment_file,
        working_dir,
    )
    write_unit_to_disk(server_unit_file, "motra-server.service")

    working_dir = entity_storage / "live"

    mexec_unit_file = motra_mexec_unit(
        user,
        group,
        python_exec,
        environment_file,
        working_dir,
    )
    write_unit_to_disk(mexec_unit_file, "motra-server-mexec@.service")

    # update systemd
    command = ["systemctl", "daemon-reload"]
    run_privileged_command(command)


@workspace_cli.command()
def env(
    all: Annotated[
        bool,
        typer.Option(help="Show all files in addition to configuration"),
    ] = False,
    tree: Annotated[
        bool,
        typer.Option(help="Show a tree view"),
    ] = False,
):
    """
    Show any workspace configuration inside the default workspace.
    """

    workspace = get_initialized_default_workspace()
    if workspace is None:
        print("No workspace found in current environment")
        raise typer.Exit()

    if not all and not tree:
        configuration_files = workspace.glob("*.config")
        files = list(configuration_files)
        fileno = len(files)
        print(f"Currently available configurations: [{fileno}] ")

        for file in files:
            with open(file) as f:
                rich.print(file)
                rich.print(JSON.from_data(json.load(f)))
                print("")

    if all:
        print("Files found: ")
        files = list(workspace.glob("**/*"))
        for file in files:
            if file.is_file():
                rich.print(f"> {file}")

    if tree:
        print(sh.tree(f"{workspace}"))


@workspace_cli.command()
def clean(
    dry_run: Annotated[
        bool,
        typer.Option(
            help="Locate and print files inside the workspace, without deleting."
        ),
    ] = True,
    all: Annotated[
        bool,
        typer.Option(
            help="Delete runtime configuration and application configruations"
        ),
    ] = False,
    archive: Annotated[
        bool,
        typer.Option(help="Delete only the measurement archives"),
    ] = False,
):
    """
    Remove existing workspace configuration
    """

    workspace = get_initialized_default_workspace()
    if workspace is None:
        print("No workspace found in current environment")
        raise typer.Exit()

    # remove the entire workspace
    if all:
        configuration_files = workspace.glob("**/*")
        files = list(configuration_files)
        fileno = len(files)
        print(f"Files marked for deleting: [{fileno}] ")

        for file in files:
            if not dry_run:
                rich.print(f"> deleting {file}")
                if file.is_file():
                    os.unlink(file)
            else:
                rich.print(f"> {file}")

    elif archive:
        configuration_files = workspace.glob("**/*")
        files = list(configuration_files)

        for file in files:
            if file.suffix == ".zip":
                if not dry_run:
                    rich.print(f"> deleting {file}")
                    if file.is_file():
                        os.unlink(file)
                else:
                    rich.print(f"> {file}")

    # only remove runtime configuration
    else:

        # create a list of currently available entities
        configuration_files = workspace.glob("*.config")
        entities = list()
        for ids in list(configuration_files):
            entities.append(ids.stem)

        # get all workspaces and remove the runtime directories
        for entity in entities:
            _, config = open_existing_workspace(entity)
            marked_files = list(config.data_storage.glob("**/*"))
            fileno = len(marked_files)
            print(f"Files marked for deleting: [{fileno}] ")

            for file in marked_files:
                if not dry_run:
                    rich.print(f"> deleting {file}")
                    if file.is_file():
                        os.unlink(file)
                else:
                    rich.print(f"> {file}")


@workspace_cli.command()
def tree():
    """
    Show a tree layout of the current motra workspace
    """

    workspace = get_initialized_default_workspace()
    if workspace is None:
        print("No workspace found in current environment")
        raise typer.Exit()
    print(sh.tree(f"{workspace}"))
