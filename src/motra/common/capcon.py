from pathlib import Path

import logging
from typing import Optional

from motra.common.capcon_protocol import CAPCON, GenericPayload

logger = logging.getLogger(__name__)


def load_capcon_from_file(workspace: Path) -> Optional[CAPCON]:
    """
    load a specific configuration from a workspace path using the entity_id.
    Loads: /workspace/path/entity_id.capcon

    returns:

    """
    # get a configuration for the current entity
    capcon_path = workspace / f"capcon.json"

    if capcon_path.exists() and capcon_path.is_file():
        capcon = capcon_path.read_text()
        logger.info("Found existing configuration")
        return CAPCON.model_validate_json(capcon)
    else:
        return None


def write_capcon_to_file(
    workspace: Path,
    current_test: CAPCON,
):
    capcon_path = workspace / f"capcon.json"
    if capcon_path.is_file():
        raise RuntimeError("Found existing configuration, not overriding.")

    # create a file ID so we have some indicator later on in the archive
    current_job = workspace / f"{current_test.CapConID}"
    current_job.touch()

    capcon_path.write_text(current_test.model_dump_json())


def write_payload_to_file(
    payload_file: Path,
    payload: GenericPayload,
):
    if payload_file.is_file():
        raise RuntimeError("Found existing configuration, not overriding.")

    payload_file.write_text(payload.model_dump_json())
