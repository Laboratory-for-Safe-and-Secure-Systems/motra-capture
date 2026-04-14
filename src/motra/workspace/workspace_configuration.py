from pathlib import Path
import typer
from typing import Literal, Union, Optional
from typing_extensions import Annotated
from pydantic import BaseModel, DirectoryPath, FilePath, Field

from motra.workspace.environment import environment_dump, environment_serialized

# https://github.com/pydantic/pydantic/issues/10559/
# uri and networking classes are broken for serialization.
# needs more checks


class ClientFileConfiguration(BaseModel):
    type: Literal["client"]
    server_uri: str
    retry_time: Annotated[int, Field(ge=0, le=30)]
    retry_limit: Annotated[int, Field(ge=0, le=30)]
    scheduling_mode: Literal["systemd", "none"]

    # workspace configuration
    live_workspace: Path
    staging_workspace: Path
    archive_workspace: Path

    def dump(self, target: Path):
        filestream = self.model_dump_json(indent=2)
        # config_path = default_workspace_path / "server.config"
        target.write_text(filestream)


class ServerFileConfiguration(BaseModel):
    type: Literal["server"]
    port: Annotated[int, Field(ge=1, le=65535)]
    host: str

    test_storage: Literal["local", "remote"]
    live_workspace: Path
    test_workspace: Union[Path, str] = Field(union_mode="left_to_right")
    archive_workspace: Path

    def dump(self, target: Path):
        filestream = self.model_dump_json(indent=2)
        # config_path = default_workspace_path / "server.config"
        target.write_text(filestream)


class FileConfiguration(BaseModel):
    config_name: str
    configuration: Union[ClientFileConfiguration, ServerFileConfiguration] = Field(
        discriminator="type"
    )
    environment: Optional[dict[str, str]] = None
    entity_storage_root: DirectoryPath
    entity_id: str
    environment_file: FilePath

    def dump(self, target_dir: Path):
        filestream = self.model_dump_json(indent=2)
        outfile = target_dir / Path(self.entity_id + ".config")
        outfile.write_text(filestream)

    # TODO create a environment file for systemd use
    def dumpenv(self):

        model = self.model_dump()
        environment_string = ""

        for node in model:
            match node:
                case "config_name" | "entity_storage_root" | "entity_id":
                    environment_string += f"MOTRA_{node.upper()}={model[node]} \n"
                case "environment":
                    environment_string += environment_serialized(model[node])

        self.environment_file.write_text(environment_string)
