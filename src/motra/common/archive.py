import logging
import zipfile
import os
import rich
from pathlib import Path

logger = logging.getLogger(__name__)


def create_archive(
    archive_name: str,
    source_directory: Path,
    target_directory: Path,
    compression_level: int = -1,
    run_post_archive_checks: bool = True,
) -> Path:
    """
    Archives an entire directory into a ZIP file in a target directory.

    Returns:
        The path to the created ZIP file, or None if an error occurred.
    """
    # --- Archiving Process ---

    config_details = {
        "archive_name": archive_name,
        "source_dir": str(source_directory),
        "target_dir": str(target_directory),
        "compression_level": compression_level,
    }
    logger.debug(
        f"Archive configuration attached ... check filestream",
        extra={"data": config_details},
    )

    # sanity checks for the provided paths
    if not Path(source_directory).is_dir():
        raise RuntimeError(f"The source '{source_directory}' is not a valid directory.")
    if not Path(source_directory).is_dir():
        raise RuntimeError(f"The target '{target_directory}' is not a valid directory.")
    if not os.access(source_directory, os.R_OK):
        raise PermissionError(f"Source directory '{source_directory}' is not readable.")
    if not os.access(target_directory, os.W_OK):
        raise PermissionError(f"Target directory '{target_directory}' is not writable.")

    archive_path = target_directory / f"{archive_name}.zip"

    # Use context manager for automatic closing
    with zipfile.ZipFile(
        archive_path,
        "w",
        zipfile.ZIP_DEFLATED,
        compresslevel=compression_level,
    ) as zf:
        # Use rglob to get all files and subdirectories recursively
        # We iterate over all paths (files and directories)
        for item_path in source_directory.rglob("*"):
            # Calculate the name inside the archive
            # This removes the arcname_base part from the full path
            arcname = item_path.relative_to(source_directory)

            if item_path.is_file():
                try:
                    zf.write(item_path, arcname=arcname)
                    logger.debug(f"Added file: '{item_path}' as '{arcname}'")
                except Exception as e:
                    logger.warning(f"Failed to add file '{item_path}' to archive: {e}")
            elif item_path.is_dir():
                # For directories, zipfile.write() adds them automatically when adding files
                # but if you want to ensure empty directories are also added, you can do:
                # zf.writestr(str(arcname) + '/', '')
                # However, rglob will yield the directory itself, and zipfile.write handles it.
                # It's usually sufficient to just add files.
                pass  # Directories are handled implicitly or explicitly via writestr if empty

    logger.info(f"Created archive: '{archive_path}'")

    if run_post_archive_checks:
        logger.info(f"Running post archive checks.")
        post_archive_checks(archive_path)

    return archive_path


def post_archive_checks(archive: Path):
    """ "
    Run some sanity checks on the archive file to determine, if the last run
    was successfull.
    """
    if not archive.exists():
        raise RuntimeError(f"Archive file '{archive.name}' was not created.")

    # check if the file size is 0
    if os.path.getsize(archive) == 0:
        raise RuntimeError(f"Archive file '{archive.name}' reports size of 0.")

    try:
        with zipfile.ZipFile(archive, "r") as zf:
            bad_file = zf.testzip()
            if bad_file:
                raise RuntimeError(
                    f"Archive integrity check failed:"
                    f"Corrupted file '{bad_file}' found in archive."
                )
            logger.debug(f"Archive '{archive.name}' integrity check passed.")
    except zipfile.BadZipFile as e:
        raise RuntimeError(f"Archive '{archive.name}' is not a valid zip file: {e}")
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred {e}")


def clean_workspace(
    workspace: Path,
    verbose: bool = False,
):
    """
    Destroys all files found in the source folder to prepare for the next test run
    """
    # Clean up previous runs, this probably breaks with recursive dirs
    if workspace.exists():
        files_to_remove = list(workspace.glob("*"))
        for file in files_to_remove:
            if verbose:
                rich.print(f"> removing {file}")
            file.unlink()
