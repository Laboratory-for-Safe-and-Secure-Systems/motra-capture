import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_logfile_from_jobid(
    job_id: str,
    workspace: Path,
):
    """
    Create a single log file inside the current live workspace from a systemd unit.

    Calls journalctl -u <...@job_id> to create a file based on the job id.
    """
    unit_name = f"motra-server-mexec@{job_id}.service"
    file_path = workspace / f"{job_id}.log"

    with open(file_path, "w") as f:
        # We pass the file object 'f' directly to stdout
        subprocess.run(
            ["journalctl", "-u", unit_name, "--no-pager"], 
            stdout=f, 
            stderr=subprocess.PIPE,
            text=True
        )