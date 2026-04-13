from pathlib import Path
import typer


def environment_serialized(env: dict) -> str:

    serialized = ""

    if env is None:
        return ""

    for key, value in env.items():
        serialized += f"{key}={value} \n"

    return serialized


def environment_dump(target: Path, environment_settings: dict[str, str]):

    serialized_env = environment_serialized(environment_settings)

    try:
        target.write(serialized_env)
    except Exception as e:
        typer.secho(
            "Failed to write environment configuration to disk.", fg=typer.colors.RED
        )
        typer.secho(f"reason: {e}", fg=typer.colors.RED)
