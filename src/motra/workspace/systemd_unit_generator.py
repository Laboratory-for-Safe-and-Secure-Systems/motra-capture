import tempfile

from pathlib import Path

from motra.common.exec_environment import (
    get_current_python_path,
    run_privileged_command,
)

from motra.common.literals import INSTALLABLE_UNITS


def reload_systemd():
    command = ["systemctl", "daemon-reload"]
    run_privileged_command(command)


def parse_systemd_config(
    user: str,
    group: str,
    environment_file: Path,
    entity_datastorage: Path,
    live_workdir: Path,
    command: str,
) -> tuple:

    python_exec = get_current_python_path() / "python3"
    exec_command = f"{python_exec} {command}"

    return {
        "user": user,
        "group": group,
        "environment": environment_file,
        "live_workdir": live_workdir,
        "entity_storage": entity_datastorage,
        "command": exec_command,
        "python": python_exec,
    }


def write_unit_to_disk(
    unit_file_contents: str,
    name: INSTALLABLE_UNITS,
):
    with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8") as temp_file:
        temp_file.write(unit_file_contents)
        temp_file.flush()

        # install the systemd configuration
        command = ["cp", temp_file.name, f"/etc/systemd/system/{name}"]
        run_privileged_command(command)


def motra_capture_unit(config: tuple) -> str:
    """
    Returns a string representation for a motra capture unit.
    Do not remove %i from the template, since this will be filled by systemd.
    """

    user = config["user"]
    group = config["group"]

    # TODO do we need capture workspace or storage workspace?
    working_dir = config["live_workdir"]

    environment_file = config["env_path"]
    command = config["command"]

    template_string = f"""
    [Unit]
    Description=Motra Measurement Capture, transient unit for test %i

    [Service]
    Type=oneshot
    User={user}
    Group={group}
    WorkingDirectory={working_dir}
    EnvironmentFile={environment_file}
    ExecStart={command}
    """

    return template_string


def motra_client_unit(config: tuple) -> str:
    """
    Returns a string representation for a motra client unit.
    Do not remove %i from the template, since this will be filled by systemd.
    """

    user = config["user"]
    group = config["group"]
    working_dir = config["entity_storage"]
    environment_file = config["environment"]
    command = config["command"]

    template_string = f"""
    [Unit]
    Description=Motra Measurement Client (Main Process), transient unit for test %i
    After=network-online.target
    Wants=network-online.target

    [Service]
    User={user}
    Group={group}
    WorkingDirectory={working_dir}
    EnvironmentFile={environment_file}
    Type=oneshot
    ExecStart={command}
    """

    return template_string


def motra_server_unit(config: tuple) -> str:
    """
    Returns a string representation for a motra server unit.
    Do not remove %i from the template, since this will be filled by systemd.
    """

    user = config["user"]
    group = config["group"]
    working_dir = config["entity_storage"]
    environment_file = config["environment"]
    command = config["command"]

    template_string = f"""
    [Unit]
    Description=Motra Measurement Server (Main Process)
    After=network-online.target
    Wants=network-online.target

    [Service]
    User={user}
    Group={group}
    WorkingDirectory={working_dir}
    EnvironmentFile={environment_file}
    Type=simple
    ExecStart={command}
    """

    return template_string


def motra_mexec_unit(config: tuple):
    """
    Returns a string representation for a motra mexec unit.
    Do not remove %i from the template, since this will be filled by systemd.
    """

    user = config["user"]
    group = config["group"]
    working_dir = config["live_workdir"]
    environment_file = config["environment"]
    python_executable = config["python"]

    template_string = f"""
    [Unit]
    Description=Motra CapCon Execution Engine (%i)
    After=network-online.target
    Wants=network-online.target

    [Service]
    User={user}
    Group={group}
    StandardOutput=journal
    StandardError=journal
    WorkingDirectory={working_dir}
    EnvironmentFile={environment_file}
    Type=exec
    ExecStart={python_executable} -m motra.cli.cli mexec %i
    """

    return template_string
