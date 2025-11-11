def environment_serialized(env: dict) -> str:

    serialized = ""

    for key, value in env.items():
        serialized += f"{key}={value} \n"

    return serialized
