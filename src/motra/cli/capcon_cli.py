from datetime import datetime, timezone
import json, sh, os, tempfile, typer, click, rich

from motra.common.capcon_protocol import GenericPayload


capcon_cli = typer.Typer(no_args_is_help=True)


@capcon_cli.command()
def gentest():
    payload = GenericPayload(
        payload_id="cap01",
        target=[
            "client",
        ],
        setup="",
        command="",
        teardown="",
        description="default test using perf",
        limits="10",
        timestamp_utc=str(datetime.now(timezone.utc)),
    )
    print(payload.model_dump_json(indent=2))
