from pydantic import BaseModel, Field, ValidationError
from typing import Optional, Type, TypeVar, Literal

import logging

logger = logging.getLogger(__name__)


# 1. Create a TypeVar named 'ModelT'.
# 2. Use 'bound=BaseModel' to specify that whatever type 'ModelT'
#    represents, it MUST be a subclass of BaseModel.
ModelT = TypeVar("ModelT", bound=BaseModel)


def validate(
    model: Type[ModelT],
    data: str,
) -> ModelT:
    """
    Checks a json string of data against a pydantic data model.
    Available message types are stored in motra.common.message_types

    Args:
        model: A pydantic class model from motra.common.message_types
        data: json string of raw data to be converted into a validated model
        config: server/client configuration for logging

    Exceptions:
        TypeError: In case the data is bad, might throw

    Returns:
        A custom response type, containing the model. Can be ERROR or SUCCESS.
        The payload is either the parsed model or failure message.
    """
    try:
        validatedModel = model.model_validate_json(data)
        logger.debug(f"Validated Model {model.__name__} successfully")
        return validatedModel
    except ValidationError as e:
        logger.error(f"failed to decode the provided JSON")
    except Exception as e:
        logger.error(
            f"Model {model.__name__} failed the verification step", exc_info={e}
        )
        return None


def validate_json(
    model: Type[ModelT],
    data: dict,
) -> ModelT:
    """
    Checks a json string of data against a pydantic data model.
    Available message types are stored in motra.common.message_types

    Args:
        model: A pydantic class model from motra.common.message_types
        data: json string of raw data to be converted into a validated model
        config: server/client configuration for logging

    Exceptions:
        TypeError: In case the data is bad, might throw

    Returns:
        A parsed pydantic data model for the specified motra base type.
    """
    validatedModel = None
    try:
        validatedModel = model.model_validate(data)
        return validatedModel
    except:
        logger.error(f"Model {model.__name__} failed the verification step")
        return None


def serialize(model: BaseModel) -> str:
    """
    Creates a serialized JSON string for sending a pydantic model over the wire

    Args:
        model: A pydantic class model from motra.common.message_types

    Returns:
        A serialized string of JSON data to send
    """
    return model.model_dump_json(indent=2)


# ============================================================================ #
#
#       CapConPayload to generate runtime configurations for the measurement
#       Client
#
#       This class is used to generate runtime configuration for the systemd
#       scheduling system that is used to create the timeframes for attacks,
#       measurements and other configurations that need to be captured in the
#       testbed.
#
# ============================================================================ #


class GenericPayload(BaseModel):
    """
    CapCon Payload for different measurement applications.
    """

    payload_type: Literal["capture", "attack"] = Field(
        description="",
        default="capture",
    )
    payload_id: str = Field(
        description="Unique ID for the payload to execute",
    )
    target: list[str] = Field(
        description="Discriminator where to run the specified payload."
        " This can hold multiple targets at a time.",
    )
    # TODO not implemented
    setup: str = Field(
        description="setup commands for the client",
    )
    command: str = Field(
        description="measurement command to execute",
    )
    # TODO not implemented
    teardown: str = Field(
        description="teardown instructions for the client",
    )
    description: str = Field(
        description="A textual description of the current test.",
    )
    # these might be changed to some custom type in the future....
    limits: int = Field(
        description="Runtime Limits in [s]",
    )
    timestamp_utc: str = Field(
        description="The ISO 8601 timestamp of when the message/object was created."
    )


# ============================================================================ #
#
#       Handshake between Client and Server
#
#       We use these in case we need to add support for more Clients later on
#       We can create unique Client IDs to run multiple sessions for cleanup
#       or teardown just in case.
#
# ============================================================================ #


class CLIENT_HELLO(BaseModel):
    """
    The very first message sent by the client upon connecting.
    It identifies the client and signals the start of the "Setup Stage".
    The Client ID can be used in case multiple clients are set up for sending
    data
    """

    message_type: Literal["CLIENT_HELLO"] = Field(
        description="The constant type identifier for this message.",
        default="CLIENT_HELLO",
    )
    client_id: str = Field(
        description="The MAC address or other unique hardware ID of the client.",
        pattern=r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",
    )
    timestamp_utc: str = Field(
        description="The ISO 8601 timestamp of when the message was created."
    )


class SERVER_HELLO(BaseModel):
    """
    The second message sent by the server upon connecting.
    It identifies the server and signals the end of the "Setup Stage".
    The Client ID can be used in case multiple clients are set up for sending
    data
    """

    message_type: Literal["SERVER_HELLO"] = Field(
        description="The constant type identifier for this message.",
        default="SERVER_HELLO",
    )
    server_id: str = Field(
        description="The MAC address or other unique hardware ID of the server.",
        pattern=r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$",
    )
    timestamp_utc: str = Field(
        description="The ISO 8601 timestamp of when the message was created."
    )


# ============================================================================ #
#
#       Message Types for File Upload
#
#       We treat files just as a set of local artifacts. For each request we
#       send a single artifact. Currently there is no good way to send the files
#       over the wire, since we just pass a base64 encoded string.
#
# ============================================================================ #


class REQUEST_UPLOAD(BaseModel):
    """
    Packet from the Client to the Server to inform the server, if we have any
    data stored locally. we also inform the server, if we do not have any data.
    """

    message_type: Literal["REQUEST_UPLOAD"] = Field(
        description="The constant type identifier for this message.",
        default="REQUEST_UPLOAD",
    )
    timestamp_utc: str = Field(
        description="The ISO 8601 timestamp of when the message was created."
    )
    file_name: str = Field(
        description="The filename of the archive. Identical to a test ID"
    )
    file_hash: str = Field(
        description="A hash over the entire file archive created when sending files"
    )
    hash_type: str = Field(
        description="The type of hash used to check the transmitted archive."
    )
    encoding: Literal["base64"] = Field(
        description="A fixed encoding when sending files over the wire."
    )
    payload: str = Field(
        description="The encoded file archive to be sent over the wire."
    )


class UPLOAD_COMPLETE(BaseModel):
    """
    Acknowledgement from the server, that we have sent all available measurement
    records.
    """

    # You can add descriptions directly to the fields
    message_type: Literal["UPLOAD_COMPLETE"] = Field(
        description="The constant type identifier for this message.",
        default="UPLOAD_COMPLETE",
    )
    timestamp_utc: str = Field(
        description="The ISO 8601 timestamp of when the message was created."
    )
    file_name: str = Field(description="The file name used for the upload")
    file_hash: str = Field(
        description="The original hash to find the file on the client side"
    )


# ============================================================================ #
#
#       Message Types for Exchanging Tests
#
#       A single Test is a JSON formatted file with a set of parameters. The
#       main parameters for the Client application are part of the message
#       body. The parameters that are part of the payload (requests) are
#       intended to be executed or used by the test executing engine.
#
# ============================================================================ #


class REQUEST_CAPCON(BaseModel):
    """
    Request from the client to perform a new measurement. This informs the server
    to send a new JSON object containing the next test case for the client.
    """

    # You can add descriptions directly to the fields
    message_type: Literal["REQUEST_CAPCON"] = Field(
        description="The constant type identifier for this message.",
        default="REQUEST_CAPCON",
    )
    timestamp_utc: str = Field(
        description="The ISO 8601 timestamp of when the message was created."
    )


class CAPCON(BaseModel):
    """
    Answer from the Server to the Client. Contains a test instance to be run on
    the client in isolated mode.
    """

    # You can add descriptions directly to the fields
    message_type: Literal["CAPCON"] = Field(
        description="The constant type identifier for this message.",
        default="CAPCON",
    )
    timestamp_utc: str = Field(
        description="The ISO 8601 timestamp of when the message was created."
    )

    CapConID: str = Field(
        description="The unique ID for the current capture configuration. "
        "Used to determine the current workspace"
    )
    description: str = Field(
        description="Textual description of the configuration(s) to be executed."
        " This is required to embed all available data and setup instructions"
        " into the final test data archive"
    )
    duration: int = Field(
        description="Time frame for the client to start the next measurement run.",
    )

    # this needs to be a payload !
    payload: Optional[list[GenericPayload]] = Field(
        description="Customized capture payloads for the different clients",
        default=None,
    )


class ACK_CAPCON(BaseModel):
    """
    Answer from the Client to the Server informing that we are ready for isolated
    mode. The answer packet to this request will trigger the client to go offline.
    """

    # You can add descriptions directly to the fields
    message_type: Literal["ACK_CAPCON"] = Field(
        description="The constant type identifier for this message.",
        default="ACK_CAPCON",
    )
    timestamp_utc: str = Field(
        description="The ISO 8601 timestamp of when the message was created."
    )
    CapConID: str = Field(description="Copy of the currently used test id.")


# ============================================================================ #
#
#       Message Types for Starting Execution
#
#       This message acts as the final trigger by the server application, once
#       all clients have been set up for a measurement. The goal is to setup
#       the service units when preparing the tests and just run the timed
#       services when the final message arrives. This way we can use the
#       network time sync to run different processes in the testbed synced.
#
# ============================================================================ #


class EXECUTE_CAPCON(BaseModel):
    """
    Final trigger from the server to the client. The client will close the active
    connection and perform the requested test in isolated mode and restart the
    client after a custom downtime.
    """

    # You can add descriptions directly to the fields
    message_type: Literal["EXECUTE_CAPCON"] = Field(
        description="The constant type identifier for this message.",
        default="EXECUTE_CAPCON",
    )
    timestamp_utc: str = Field(
        description="The ISO 8601 timestamp of when the message was created."
    )
    CapConID: str = Field(description="copy of the currently used test id.")
