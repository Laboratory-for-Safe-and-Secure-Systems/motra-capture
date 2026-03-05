from capcon.payload import genPayload, GenericPayload


logging_payloads = []
logging_payloads.append(
    genPayload(
        command="docker ps",
        description="get container health state",
        limits="1s",
        offset="200ms",
        payload_type="logs",
    )
)

logging_payloads.append(
    genPayload(
        command="docker container logs plc-logic --tail 20",
        description="check client plc-logic health",
        limits="1s",
        offset="200ms",
        payload_type="logs",
    )
)

logging_payloads.append(
    genPayload(
        command="docker container logs plc-server --tail 20",
        description="check client plc-server health",
        limits="1s",
        offset="200ms",
        payload_type="logs",
    )
)

logging_payloads.append(
    genPayload(
        command="docker container logs plc-historian --tail 20",
        description="check client plc-historian health",
        limits="1s",
        offset="200ms",
        payload_type="logs",
    )
)
