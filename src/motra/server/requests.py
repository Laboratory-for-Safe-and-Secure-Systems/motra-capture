from pathlib import Path
from motra.common.capcon_protocol import *
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def parse_SERVER_HELLO() -> SERVER_HELLO:
    """
    Creates a pydantic SERVER_HELLO model for further parsing
    """
    response = SERVER_HELLO(
        server_id="00:00:00:00:00:00",  # TODO: implement the hw IDs
        timestamp_utc=str(datetime.now(timezone.utc)),
    )
    logger.debug(
        f"Server: Parsing SERVER_HELLO header for {response.server_id}... ",
        extra={"data": response},
    )
    return response


def parse_CAPCON(pending_test: Path) -> CAPCON:
    """
    Creates a pydantic PREPARE_TEST model for further parsing. Can return an
    empyt model, in case the server does not have anymore tests to run.
    """
    response = None
    if pending_test:

        # parsed_file_for_sending = util.parse_json_file_to_dict(pending_test)
        # print(parsed_file_for_sending.get("payload"))

        if pending_test.exists():
            capcon_json = pending_test.read_text()
            logger.info(f"Loading Capcon {pending_test}")
            response = CAPCON.model_validate_json(capcon_json)
    else:
        logger.info("Server: Executed all available tests, stopping... ")
        response = CAPCON(
            timestamp_utc=str(datetime.now(timezone.utc)),
            command="",
            CapConID="",
            description="",
            duration=0,
        )

    logger.debug(
        "Server: Parsing PREPARE_TEST header... ",
        extra={"data": response},
    )
    return response


def parse_UPLOAD_COMPLETE(request: BaseModel) -> UPLOAD_COMPLETE:
    """
    Creates a pydantic UPLOAD_COMPLETE model for further parsing. Uses the
    initial request to pass additional data between server and client.
    """
    response = UPLOAD_COMPLETE(
        timestamp_utc=str(datetime.now(timezone.utc)),
        file_name=request.file_name,
        file_hash=request.file_hash,
    )
    logger.debug(
        "Server: Parsing UPLOAD_COMPLETE header... ",
        extra={"data": response},
    )

    return response


def parse_EXECUTE_CAPCON(current_test_id: str) -> EXECUTE_CAPCON:
    """
    Creates a pydantic EXECUTE_TEST model for further parsing. Execute test
    serves as a custom trigger with an additional timestamp for logging
    purposes. Does not server any other purpose.
    """
    response = EXECUTE_CAPCON(
        timestamp_utc=str(datetime.now(timezone.utc)),
        CapConID=current_test_id,
    )
    logger.debug(
        "Server: Parsing EXECUTE_TEST heades... ",
        extra={"data": response},
    )

    return response
