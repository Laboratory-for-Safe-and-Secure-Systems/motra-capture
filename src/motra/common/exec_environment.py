import sys, subprocess
import logging

from pathlib import Path

logger = logging.getLogger(__name__)


def get_current_python_path():

    # get the current python executable
    python_executable_path = sys.executable

    if python_executable_path is None:
        raise ValueError(
            "Current environment did not return a valid Python executable!"
        )

    logger.debug(f"Got current python executable {python_executable_path}")

    # since the string from earlier is /../bin/pythonXYZ this sould remove the trailer
    python_executable_path = Path(python_executable_path).parent
    logger.debug(f"Expected Path: {python_executable_path}")

    return python_executable_path


def run_privileged_command(command: list[str]):
    """
    Runs a command using sudo, prompting the user for a password interactively.

    Args:
        command: A list of strings representing the command and its arguments.
                 Example: ['ls', '-l', '/root']
    """
    try:
        full_command = ["sudo"] + command
        print(f"--> Running command: {' '.join(full_command)}")
        result = subprocess.run(full_command, check=True)
        print(f"--> Command finished successfully with exit code: {result.returncode}")

    except FileNotFoundError:
        print(f"Error: 'sudo' command not found. Is it in your PATH?")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with exit code {e.returncode}.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n--> User cancelled the operation.")
        sys.exit(1)
