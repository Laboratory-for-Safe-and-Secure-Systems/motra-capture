import json, sh, os, typer, click, rich
from pathlib import Path
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
    parse_systemd_config,
    reload_systemd,
    write_unit_to_disk,
)
from motra.workspace.workspace import (
    create_entity_workspace,
    get_initialized_default_workspace,
    init_entity_workspace_dir,
    open_existing_workspace,
)
from motra.workspace.workspace_configuration import (
    ClientFileConfiguration,
    FileConfiguration,
    ServerFileConfiguration,
)

from motra.workspace.environment import environment_dump, environment_serialized


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
    prefered_workspace: Path = None,
):
    """
    Create a workspacesconfiguration for a MOTRA client
    """
    typer.secho("Generating a new CLIENT configuration ...", fg=typer.colors.GREEN)

    # this will get the default or fallback directory for workspaces
    default_workspace_path, existingconf = init_entity_workspace_dir(
        prefered_workspace, entity
    )
    entity_storage = default_workspace_path / entity
    create_entity_workspace({entity: entity_storage})

    typer.secho(
        f"Selected workspace: {default_workspace_path}for {entity}",
        fg=typer.colors.GREEN,
    )

    environment_addons = {
        "MOTRA_WORKSPACE": str(default_workspace_path),
        f"MOTRA_{entity.upper()}_WORKSPACE": str(
            default_workspace_path / f"{entity}.config"
        ),
    }

    environment_file = entity_storage / Path(entity + ".env")
    if environment_file.exists():
        typer.secho("Found existing configuration.", fg=typer.colors.YELLOW)
    else:
        environment_file.touch()

    # generate a default config
    clientconfig = ClientFileConfiguration(
        type="client",
        server_uri=server_uri,
        retry_time=retry_time,
        retry_limit=retry_limit,
        scheduling_mode=scheduling_mode,
        live_workspace=entity_storage / "live",
        staging_workspace=entity_storage / "staging",
        archive_workspace=entity_storage / "archive",
    )

    appconfig = FileConfiguration(
        config_name=f"client-{entity}",
        configuration=clientconfig,
        environment=environment_addons,
        environment_file=environment_file,
        entity_storage_root=entity_storage,
        entity_id=entity,
    )

    # dump current configuration to TUI
    typer.secho("Generated workspace configuration: ", fg=typer.colors.GREEN)
    rich.print(JSON(appconfig.model_dump_json()))
    typer.confirm("Is the current configuration correct?", abort=True)

    # find currenty exported workspace (either by env or by fallback/user session)
    if existingconf:
        # we need to warn before overriding later on
        typer.secho(
            f"Checking existing data. Found existing CLIENT workspace"
            f"in {default_workspace_path}",
            fg=typer.colors.YELLOW,
        )
        rich.print(JSON(existingconf.model_dump_json()))
        typer.confirm("Override existing configuration?", abort=True)

    # store configuration to disk
    typer.secho("Writing files to disk ", fg=typer.colors.GREEN)

    # filestream = appconfig.model_dump_json(indent=2)
    # config_path = default_workspace_path / f"{entity}.config"
    # config_path.write_text(filestream)

    # env_path = default_workspace_path / f"{entity}.env"
    # env_path.write_text(environment_serialized(env_setting))

    # setup  systemd templates for the generated confguration
    # python_exec = get_current_python_path() / "python3"
    # command = f"{python_exec} -m motra.cli.cli client"
    # environment_file = env_path
    # working_dir = entity_storage

    appconfig.dump(default_workspace_path)
    appconfig.dumpenv()

    # update the local workspace paths
    client_workspace = {
        "live": clientconfig.live_workspace,
        "archive": clientconfig.archive_workspace,
        "stage": clientconfig.staging_workspace,
    }
    create_entity_workspace(client_workspace)

    sysd_config = parse_systemd_config(
        user=os.getuid(),
        group=os.getgid(),
        command="-m motra.cli.cli client",
        environment_file=appconfig.environment_file,
        entity_datastorage=appconfig.entity_storage_root,
        live_workdir=appconfig.configuration.live_workspace,
    )

    # create the client template unit
    client_unit_file = motra_client_unit(sysd_config)

    write_unit_to_disk(client_unit_file, "motra-client@.service")

    # TODO, this needs to be fixed; storage is not maintained here atm.
    # working_dir = entity_storage / "live"
    # sysd_config["workdir"] = appconfig.configuration.live_workspace

    # create the measurement unit
    capture_unit_file = motra_mexec_unit(sysd_config)
    write_unit_to_disk(capture_unit_file, "motra-client-mexec@.service")

    # update systemd
    reload_systemd()


@workspace_cli.command()
def server(
    host: Annotated[
        str, typer.Option(prompt="Which IP/host should be used for the server: ")
    ] = "0.0.0.0",
    port: Annotated[int, typer.Option(prompt="Set the default port: ")] = 12400,
    server_workspace_override: Path = None,
):
    """
    Create a workspace configuration for a MOTRA server
    """
    typer.secho("Generating a new SERVER configuration ...", fg=typer.colors.GREEN)

    # this will get the default workspace directory
    default_entity = "server"

    default_workspace_path, existingconf = init_entity_workspace_dir(
        server_workspace_override, default_entity
    )
    entity_storage = default_workspace_path / default_entity
    create_entity_workspace({default_entity: entity_storage})
    typer.secho(
        f"Selected workspace: {default_workspace_path} for {default_entity}",
        fg=typer.colors.GREEN,
    )

    # set workspace specific additions, we will add these to FileConfiguration
    # we will change the env_dump to use the FileConfiguration
    environment_addons = {
        "MOTRA_WORKSPACE": str(default_workspace_path),
        "MOTRA_SERVER_WORKSPACE_CONFIG": str(
            default_workspace_path / f"{default_entity}.config"
        ),
    }
    environment_file = entity_storage / Path(default_entity + ".env")
    if environment_file.exists():
        typer.secho("Found existing configuration.", fg=typer.colors.YELLOW)
    else:
        environment_file.touch()

    # generate a default config
    serverconfig = ServerFileConfiguration(
        type="server",
        port=port,
        host=host,
        test_storage="local",  # start the per default server in local mode
        live_workspace=entity_storage / "live",
        test_workspace=entity_storage / "tests",
        archive_workspace=entity_storage / "archive",
    )

    appconfig = FileConfiguration(
        config_name="server-default",
        configuration=serverconfig,
        environment=environment_addons,
        entity_storage_root=entity_storage,
        entity_id=default_entity,
        environment_file=environment_file,
    )

    # dump current configuration somewhere
    typer.secho("Generated workspace configuration: ", fg=typer.colors.GREEN)
    rich.print(JSON(appconfig.model_dump_json()))
    typer.confirm("Is the current configuration correct?", abort=True)

    # prompt the user, if we need to override the existing configuration or keep the old one
    if existingconf:
        typer.secho(
            f"Checking existing data. Found existing SERVER workspace "
            f"in {default_workspace_path}",
            fg=typer.colors.YELLOW,
        )
        rich.print(JSON(existingconf.model_dump_json()))
        typer.confirm("Override existing configuration?", abort=True)

    typer.secho("Writing files and configuration to disk ", fg=typer.colors.GREEN)
    appconfig.dump(default_workspace_path)
    appconfig.dumpenv()

    # update the local workspace paths
    server_workspace = {
        "live": serverconfig.live_workspace,
        "archive": serverconfig.archive_workspace,
        "tests": serverconfig.test_workspace,
    }
    create_entity_workspace(server_workspace)

    sysd_config = parse_systemd_config(
        user="root",
        group="root",
        command="-m motra.cli.cli server",
        environment_file=appconfig.environment_file,
        entity_datastorage=appconfig.entity_storage_root,
        live_workdir=appconfig.configuration.live_workspace,
    )

    # generate files for the server unit
    server_unit_file = motra_server_unit(sysd_config)
    write_unit_to_disk(server_unit_file, "motra-server.service")

    # generate files for the server side mexec executor
    # sysd_config["workdir"] = appconfig.configuration.live_workspace
    mexec_unit_file = motra_mexec_unit(sysd_config)
    write_unit_to_disk(mexec_unit_file, "motra-server-mexec@.service")

    # update systemd configuration to make changes globally available
    reload_systemd()


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
        typer.secho(
            f"Currently available configurations: [{fileno}] ", fg=typer.colors.GREEN
        )

        for file in files:
            with open(file) as f:
                rich.print(file)
                rich.print(JSON.from_data(json.load(f)))
                typer.secho("")

    if all:
        print("Files found: ")
        files = list(workspace.glob("**/*"))
        for file in files:
            if file.is_file():
                rich.print(f"> {file}")

    if tree:
        typer.secho(sh.tree(f"{workspace}"), fg=typer.colors.GREEN)


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
            help="Delete runtime configuration and application configurations"
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

    # TODO scan for entitiy config and load the workspace setup from there
    # this way file handling will be far simpler
    workspace = get_initialized_default_workspace()
    if workspace is None:
        typer.secho(
            "No configured workspace found in current environment",
            fg=typer.colors.RED,
        )
        raise typer.Exit()

    # remove the entire workspace
    if all:
        configuration_files = workspace.glob("**/*")
        files = list(configuration_files)
        fileno = len(files)
        typer.secho(f"Files marked for deleting: [{fileno}] ", fg=typer.colors.RED)

        for file in files:
            if not dry_run:
                typer.secho(f"> deleting {file}", fg=typer.colors.YELLOW)
                if file.is_file():
                    os.unlink(file)
            else:
                typer.secho(f"> {file}", fg=typer.colors.GREEN)

    elif archive:
        configuration_files = workspace.glob("**/*.zip")
        files = list(configuration_files)
        fileno = len(files)
        typer.secho(f"Files marked for deleting: [{fileno}] ", fg=typer.colors.RED)

        for file in files:
            if file.suffix == ".zip":
                if not dry_run:
                    typer.secho(f"> deleting {file}", fg=typer.colors.YELLOW)
                    if file.is_file():
                        os.unlink(file)
                else:
                    typer.secho(f"> {file}", fg=typer.colors.GREEN)

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
            # python can deduct sets and cast into lists:
            marked_files = list(
                set(config.entity_storage_root.glob("**/*"))
                - set(config.entity_storage_root.glob("**/*.env"))
            )
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
