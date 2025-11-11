import shlex
import shutil
import subprocess
import logging

from motra.common.exec_environment import get_current_python_path

from motra.common.literals import MOTRA_UNITS

logger = logging.getLogger(__name__)


COMMAND = list[str]


def generate_scheduler_template(
    unit_type: MOTRA_UNITS,
    current_id: str,
    start_time_delta: str,
    default_timer_accuracy: str = "10ms",
    template_unit: bool = True,
) -> COMMAND:

    if template_unit:
        template = "@"
    else:
        template = ""

    command = f"""sudo 
                    systemd-run 
                    --on-active={start_time_delta} 
                    --unit {unit_type}{template}{current_id}.service 
                    --timer-property AccuracySec={default_timer_accuracy}"""

    return shlex.split(command)


def execute_scheduler_template(command: COMMAND):

    if len(command) == 0:
        raise ValueError("cannot run an empty command.")

    logger.info(f"Executing {command}")

    # resolve the main executable
    process_executable = shutil.which(command[0])
    if process_executable is None:
        raise ValueError("Executable could not be found.")

    command[0] = process_executable

    try:
        # subprocess.run() is a blocking call.
        # capture_output=True: Captures stdout and stderr.
        # text=True: Decodes stdout/stderr as text using the default encoding.
        # check=True: Raises CalledProcessError if the command returns a non-zero exit code.
        result = subprocess.run(command, shell=False, capture_output=True, text=True)

        if result.returncode == 0:
            logger.info("Command executed successfully.")
            logger.info(f"  STDOUT: >> {result.stdout} <<s ")
            if len(result.stderr) > 0:
                logger.info(f"  STDERR: >> {result.stderr} <<  ")
        else:
            logger.error(f"Command failed with exit code {result.returncode}")
            logger.error(f"  STDOUT: >> {result.stdout} <<  ")
            if len(result.stderr) > 0:
                logger.error(f"  STDERR: >> {result.stderr} << ")

    except FileNotFoundError:
        logger.error(f"Error: Command or executable not found.")


def schedule_capture_process(test_id: str):
    """
    Starts a capture unit to perform system measurements.
    Currently supported are:
        1. Hardware measurements

    Args:
        config: stores the main client configuration to handle working directories and other dependencies like python environments
        command: a custom command to pass into the scheduling function. however this is not implemented

    """

    command = [
        "sudo",
        "systemd-run",
        "--on-active=2s",
        f"--unit motra-mexec@{test_id}.service",
        "--timer-property AccuracySec=10ms",
    ]

    try:
        # subprocess.run() is a blocking call.
        # capture_output=True: Captures stdout and stderr.
        # text=True: Decodes stdout/stderr as text using the default encoding.
        # check=True: Raises CalledProcessError if the command returns a non-zero exit code.
        result = subprocess.run(
            " ".join(command), shell=True, check=True, capture_output=True, text=True
        )

        logger.info("Command executed successfully.")
        logger.info("STDOUT:")
        logger.info(f" || >> {result.stdout} << || ")
        if result.stderr:
            logger.info("STDERR:")
            logger.info(f" || >> {result.stderr} << || ")

    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error("STDOUT:")
        logger.error(f" || >> {e.stdout} << || ")
        logger.error("STDERR:")
        logger.error(f" || >> {e.stderr} << || ")
    except FileNotFoundError:
        logger.error(f"Error: Shell command not found.")


def schedule_client_process(awake: int, current_id: str):
    """
    Schedules the next Client Instance to be run after a test.
    The wake value is used to restart the client session after x seconds.
    The ID parameter is used to pass the test ID into systemd to spawn a new template instance.

    Args:
        config: Current Client configuration.
        awake: Time in seconds for the scheduler to respawn the client process.
        current_id: Test ID to generate a new unit instance for systemd.
    """

    # https://www.freedesktop.org/software/systemd/man/latest/systemd.time.html#
    # systemd time spans
    command = [
        "sudo",
        "systemd-run",
        f"--on-active={awake}",
        f"--unit motra-client@{current_id}.service",
        "--timer-property AccuracySec=10ms",
    ]

    commandstr = " ".join(command)

    logger.debug(f"Command: {commandstr}")

    try:
        # subprocess.run() is a blocking call.
        # capture_output=True: Captures stdout and stderr.
        # text=True: Decodes stdout/stderr as text using the default encoding.
        # check=True: Raises CalledProcessError if the command returns a non-zero exit code.
        result = subprocess.run(
            " ".join(command), shell=True, check=True, capture_output=True, text=True
        )

        logger.info("Command executed successfully.")
        logger.info("STDOUT:")
        logger.info(f" || >> {result.stdout} << || ")
        if result.stderr:
            logger.info("STDERR:")
            logger.info(f" || >> {result.stderr} << || ")

    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error("STDOUT:")
        logger.error(f" || >> {e.stdout} << | ")
        logger.error("STDERR:")
        logger.error(f" || >> {e.stderr} << || ")
    except FileNotFoundError:
        logger.error(f"Error: Shell command not found.")
