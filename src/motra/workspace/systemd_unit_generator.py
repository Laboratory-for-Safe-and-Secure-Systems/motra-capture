import tempfile

from motra.common.exec_environment import run_privileged_command

from motra.common.literals import INSTALLABLE_UNITS


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


def motra_capture_unit(
    user: str,
    group: str,
    command: str,
    environment_file: str,
    working_dir: str,
) -> str:
    """
    Returns a string representation for a motra capture unit.
    Do not remove %i from the template, since this will be filled by systemd.
    """

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


def motra_client_unit(
    user: str,
    group: str,
    command: str,
    environment_file: str,
    working_dir: str,
) -> str:
    """
    Returns a string representation for a motra client unit.
    Do not remove %i from the template, since this will be filled by systemd.
    """

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


def motra_server_unit(
    user: str,
    group: str,
    command: str,
    environment_file: str,
    working_dir: str,
) -> str:
    """
    Returns a string representation for a motra server unit.
    Do not remove %i from the template, since this will be filled by systemd.
    """

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


def motra_mexec_unit(
    user: str,
    group: str,
    python_executable: str,
    environment_file: str,
    working_dir: str,
):
    """
    Returns a string representation for a motra mexec unit.
    Do not remove %i from the template, since this will be filled by systemd.
    """

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
    Type=oneshot
    ExecStart={python_executable} -m motra.cli.cli mexec %i
    """

    return template_string
