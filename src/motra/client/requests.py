from pydantic import ValidationError
from datetime import datetime, timezone
from pathlib import Path

from motra.common.capcon_protocol import *
from motra.common.response_types import Status, Response
from motra.common import util

logger = logging.getLogger(__name__)


def parse_CLIENT_HELLO() -> Response:
    request = CLIENT_HELLO(
        client_id="00:00:00:00:00:00",  # TODO: implement the hw IDs
        timestamp_utc=str(datetime.now(timezone.utc)),
    )

    logger.debug(
        "Client: Parsed CLIENT_HELLO header",
        extra={"data": request.model_dump()},
    )

    return Response(status=Status.SUCCESS, payload=request)


def parse_REQUEST_UPLOAD(
    file: Path,
) -> Response:

    digest = util.create_sha256(file)
    base64_stream = util.create_base64_file_stream(file)
    request = None

    try:
        request = REQUEST_UPLOAD(
            timestamp_utc=str(datetime.now(timezone.utc)),
            file_name=file.name,
            file_hash=digest,
            hash_type="sha256",
            encoding="base64",
            payload=base64_stream,
        )

    except ValidationError as e:
        logger.error(
            f"Client:  REQUEST_UPLOAD request failed to validate, \n {e}",
            exc_info=True,
        )
        return Response(status=Status.ERROR, payload="Validation failed")

    logger.debug(
        "Client: Parsed REQUEST_UPLOAD header",
        extra={"data": request.model_dump()},
    )

    return Response(status=Status.SUCCESS, payload=request)


def parse_REQUEST_CAPCON() -> Response:
    request = REQUEST_CAPCON(
        timestamp_utc=str(datetime.now(timezone.utc)),
        hardware_info="testing",
    )

    logger.debug(
        "Client: Parsed REQUEST_TEST header",
        extra={"data": request.model_dump()},
    )

    return Response(status=Status.SUCCESS, payload=request)


def parse_ACK_CAPCON(current_test_id: str) -> Response:
    request = ACK_CAPCON(
        hardware_info="tbd",
        timestamp_utc=str(datetime.now(timezone.utc)),
        CapConID=current_test_id,
    )

    logger.debug(
        "Client: Parsed ACK_PREPARE_TEST header",
        extra={"data": request.model_dump()},
    )

    return Response(status=Status.SUCCESS, payload=request)
