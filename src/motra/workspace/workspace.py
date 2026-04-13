import os
import logging
import pwd
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from motra.workspace.workspace_configuration import FileConfiguration


def get_default_workspace_path(preferred_path: Path) -> Path:
    """
    Tries to guess the default workspace from the environment.

    Checked Defaults:
    1) Read MOTRA_WORKSPACE from the environment \n
    2) Preferred Path, if provided
    3) /home/<user>/.local/share/motra as a default

    Using XDG_RUNTIME_DIR does not work for multiple reasons:
    1. we need to setup lingering to not wipe any measurement data in case of reboot or logout
    2. since /run/user/<uid> is a tmpfs, there are very strict memory limits. 800MB of data can be wasted quickly

    returns:
        Path: The workspace, as found in the default order (raises on error)
    """
    target_workdir = None
    xdg_runtime_dir = None
    # systemd does not work this way with runtime_dir, since this was an sandboxing option

    custom_workspace = os.environ.get("MOTRA_WORKSPACE")
    if custom_workspace:
        target_workdir = Path(custom_workspace).absolute()
        logger.info(f"Selected workspace: {target_workdir}")
        return target_workdir

    if preferred_path:
        # if path is relative, create a sanitized path here
        logger.info(f"Using provided Path: {Path(preferred_path).absolute()}")
        target_workdir = Path(preferred_path).absolute()

    else:
        # we need to fall back to a sane default to init the application
        user = pwd.getpwuid(os.getuid())[0]
        target_workdir = Path(f"/home/{user}/.local/share/motra").absolute()

    logger.info(f"Selected workspace: {target_workdir}")

    return target_workdir


def get_initialized_default_workspace() -> Optional[Path]:
    """
    Uses the default search order to find an initialized workspace

    Checked Defaults:
    1) Read MOTRA_WORKSPACE from the environment \n
    2) check XDG_RUNTIME_DIR for a user session \n
    3) check /run/user/<userid>/motra/ for a default fallback

    returns:
        Path | None: A path to a initialized workspace
    """

    path = get_default_workspace_path(None)
    if workspace_config_present(path, None):
        return path

    return None


def workspace_config_present(path: Path, entity: str | None) -> bool:
    """
    Checks if a path contains a configuration file
    If only a path is given, checks *.config. If an entity is given, checks if
    path contains entity.config.

    Parameters:
        path (Path): The location to look for workspace files
        entity: check for a specific configuration
    Returns:
        Bool: True if a configuratios was found, false otherwise
    """

    # is the path provided valid?
    if not (path.exists() and path.is_dir()):
        return False

    configuration_files = path.glob("*.config")

    if entity is None:

        # do any configuration files exist?
        if len(list(configuration_files)) == 0:
            return False
        else:
            return True

    else:
        # does a specific configuration exist?
        if entity is not None and entity in list(configuration_files):
            return True
        else:
            return False


def get_validated_workspace_configuration(
    path: Path, entity: str
) -> Optional[BaseModel]:
    """
    Query and validate a workspace configuration and return the configuration.

    Parameters:
        path: The location to look for a workspace
        entity: The exact configuration entity <client/server>
    Returns:
        BaseModel: Either a model or None if no configuration was found.
    """

    if workspace_config_present(path, entity) == None:
        return None

    configuration_location = path / f"{entity}.config"
    if configuration_location.exists():
        workspace_config = configuration_location.read_text()
        logger.info("Found existing configuration")
        return FileConfiguration.model_validate_json(workspace_config)
    else:
        return None


def init_entity_workspace_dir(
    preferred_path: Optional[str],
    entity: str,
) -> tuple[Path, FileConfiguration | None]:
    """
    Open an existing workspace directory or create an empy one. If no path is
    provided, the defaults are checked.

    Parameters:
        preferred_path (Path): Target workspace (optional)
        entity (str): can be "client" or "server"
    Returns:
        tuple[Path, BaseModel | None]: A Path to a valid workspace.
        And a validated configuration file, if one was present.
    """

    path = get_default_workspace_path(preferred_path)

    # perform checks on the existing workspace ...
    # this should probably be a pydantic class to load the default configuration
    configuration = get_validated_workspace_configuration(path, entity)

    # check if the requested entity is the correct one
    # pydantic will check the literals, however the encoded type could be mixed up
    if configuration and not configuration.configuration.type == entity:
        raise ValueError("Not a valid server configuration")

    # check if previous workspace is empty
    # if we dont have existing data, create the root for later use and exit
    else:
        logger.debug("No existing configuration present, creating empyt workspace")
        create_entity_workspace({entity: path})
        # path.mkdir(parents=True, exist_ok=True)

    return (path, configuration)


def open_existing_workspace(entity: str) -> Optional[tuple[Path, FileConfiguration]]:
    """
    Gets an existing, valid workspace + configuration.

    Parameters:
        entity (str): can be "client+ID" or "server"
    Returns:
        [Path + BaseModel | None]: A Path and configuration to a valid
        workspace of a selected entity.
    """

    workspace = get_default_workspace_path(None)
    configuration = get_validated_workspace_configuration(workspace, entity)

    if configuration is None:
        return None

    return (workspace, configuration)


def create_entity_workspace(workspaces: dict[str, Path]) -> None:
    for workspace in workspaces.values():
        workspace.mkdir(exist_ok=True, parents=True)
