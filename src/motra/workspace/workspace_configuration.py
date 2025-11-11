from typing import Literal, Union, Optional
from typing_extensions import Annotated
from pydantic import BaseModel, DirectoryPath, Field

# https://github.com/pydantic/pydantic/issues/10559/
# uri and networking classes are broken for serialization.
# needs more checks


class ClientFileConfiguration(BaseModel):
    type: Literal["client"]
    server_uri: str
    retry_time: Annotated[int, Field(ge=0, le=30)]
    retry_limit: Annotated[int, Field(ge=0, le=30)]
    scheduling_mode: Literal["systemd", "none"]


class ServerFileConfiguration(BaseModel):
    type: Literal["server"]
    port: Annotated[int, Field(ge=1, le=65535)]
    host: str
    test_storage: Optional[str] = None  # TODO: implement local | remote


class FileConfiguration(BaseModel):
    config_name: str
    configuration: Union[ClientFileConfiguration, ServerFileConfiguration] = Field(
        discriminator="type"
    )
    environment: Optional[dict[str, str]] = None
    data_storage: DirectoryPath
