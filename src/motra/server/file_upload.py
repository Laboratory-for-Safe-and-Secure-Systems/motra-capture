import base64
import logging
from pathlib import Path
from motra.common.capcon_protocol import REQUEST_UPLOAD


logger = logging.getLogger(__name__)


def handle_file_payload(request: REQUEST_UPLOAD, workspace: Path):
    """
    Stores a received file to disk. Uses the encoding provided by the request
    to decode a file into a bytestream and writes the raw file to disk.
    """

    try:
        # store the received file
        filename = request.file_name
        base64_str = request.payload

        # TODO add hash handling
        # received_file_hash = request["file_hash"]
        # hash_type = request["hash_type"]

        logger.info(f"Receiving file: {filename}")

        file_path = workspace / f"{filename}"
        file_path = file_path.resolve()

        # TODO what happens, if files are existing
        if file_path.exists():
            raise RuntimeError("Capture archive already exists.")

        file_bytes = base64.b64decode(base64_str)
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        logger.info(f"Successfully saved file to: {file_path}")

    except base64.binascii.Error as e:
        logger.error(f"Base64 decoding error for {filename}: {e}")
    except Exception as e:
        logger.error(f"An error occurred while saving {filename}: {e}")
        # TODO missing return statement!
