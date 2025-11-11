import json, hashlib, base64, logging
from pathlib import Path
from typing import Dict, Any, Optional

from motra.common.capcon_protocol import *
from motra.common.response_types import Response, Status

logger = logging.getLogger(__name__)


def parse_json_file_to_dict(
    file_path: Path,
) -> Optional[Dict[str, Any]]:
    """
    Reads a file from disk and parses its content as JSON.

    Args:
        file_path: A pathlib.Path object pointing to the JSON file.

    Returns:
        A dictionary representing the JSON content if successful,
        otherwise None.
    """
    # 1. Check if the file actually exists before trying to open it.
    if not file_path.is_file():
        logger.error(f"File not found at '{file_path}'")
        return None

    try:
        # 2. Open the file in text read mode ('r') with UTF-8 encoding.
        #    Specifying the encoding is a best practice.
        with open(file_path, "r", encoding="utf-8") as f:
            # 3. Use json.load() to read from a file-like object and parse it.
            #    This is slightly more direct than reading to a string first.
            data = json.load(f)

        # Ensure the top-level object is a dictionary, as is common for configs.
        if not isinstance(data, dict):
            logger.error(f"JSON content in '{file_path}' is not a dictionary (object).")
            return None

        return data

    except json.JSONDecodeError as e:
        # This error occurs if the file content is not valid JSON.
        logger.error(
            f"Failed to parse JSON from '{file_path}'. Invalid format.",
            exc_info=True,
        )
        return None
    except Exception as e:
        # Catch any other potential errors (e.g., permission denied).
        logger.error(
            f"An unexpected error occurred while reading '{file_path}'.",
            exc_info=True,
        )
        return None


def save_model_to_json_file(
    model_instance: BaseModel,
    file_path: Path,
):
    """
    Serializes a Pydantic model to a JSON string and saves it to a file.

    Args:
        model_instance: The Pydantic model instance to save.
        file_path: A pathlib.Path object for the output file.
    """
    logger.info(f"Attempting to save model to: {file_path}")
    try:
        # 1. Serialize the model to a JSON string with indentation for readability.
        #    indent=2 is a common choice for pretty-printing.
        json_string = model_instance.model_dump_json(indent=2)

        # 2. Write the string to the specified file.
        #    'w' for write mode, and 'utf-8' is the standard encoding.
        file_path.write_text(json_string, encoding="utf-8")
        logger.info(f"Successfully saved model to file.")

    except Exception as e:
        logger.error(f"An error occurred while saving the file.", exc_info=True)


def load_json_files_into_list(
    pending_files: list[Path],
) -> Response:
    loaded_data = list()
    for file_path in pending_files:
        logger.debug(f"Reading '{file_path.name}'...")
        try:
            # Open in text read mode with UTF-8 encoding
            with open(file_path, "r", encoding="utf-8") as f:
                # Use json.load() to parse the file object
                data = json.load(f)
                loaded_data.append(data)
                logger.debug(f"success")

        except json.JSONDecodeError:
            # Handle files with invalid JSON content
            logger.error(
                f"Failed to parse JSON. Invalid format.",
                exc_info=True,
            )
            return Response(status=Status.ERROR)
        except Exception:
            # Handle other potential errors (e.g., permission issues)
            logger.error(
                f"An unexpected error occurred while reading the file.",
                exc_info=True,
            )
            return Response(status=Status.ERROR)

    return Response(status=Status.SUCCESS, payload=loaded_data)


def move_file(source: Path, destination: Path):
    """
    Moves/renames a file or directory using pathlib.Path.rename().
    pathlib does NOT handle the case for destination beeing a directory. Both
    parameters need to be a fully qualified file path.
    """
    try:
        source.rename(destination)
        logger.debug(f"Moved '{source}' to '{destination}' successfully.")
    except FileNotFoundError:
        logger.error(f"Error: Source '{source}' not found.")
    except OSError as e:
        logger.error(f"Error moving '{source}' to '{destination}': {e}")


def check_id_uniqueness(
    items: list,
    key: str,
) -> bool:
    ids = [item.get(key) for item in items if item.get(key) is not None]
    if len(ids) == len(set(ids)):
        return Response(status=Status.SUCCESS)
    else:
        logger.error(f"A non unique key has been found in the test files")
        return Response(status=Status.ERROR)


def create_sha256(file: Path) -> str:
    # hash the file to generate a footprint for the archive
    hash_algo = "sha256"
    hasher = hashlib.new(hash_algo)
    with open(file, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def create_base64_file_stream(file: Path):
    # encode the data into a base64 stream for sending
    file_bytes = file.read_bytes()
    return base64.b64encode(file_bytes).decode("ascii")
