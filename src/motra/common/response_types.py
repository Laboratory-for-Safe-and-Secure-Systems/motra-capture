from pydantic import BaseModel
from typing import Literal, Any, Optional
from enum import Enum


class Status(Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    CONNECTION_CLOSED = "CONNECTION_CLOSED"
    CONNECTION_FAILED = "CONNECTION_FAILED"


# class ErrorDetails(BaseModel):
#     code: int
#     message: str
#     details: Optional[str] = None


class Response(BaseModel):
    """A structured response from a generic call or method."""

    status: Literal[
        Status.SUCCESS, Status.ERROR, Status.CONNECTION_CLOSED, Status.CONNECTION_FAILED
    ]
    payload: Optional[Any] = None
    # error: Optional[ErrorDetails] = None
