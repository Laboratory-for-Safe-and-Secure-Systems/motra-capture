from capcon.util.payload import genPayload, GenericPayload


logging_payloads: list[GenericPayload] = []
logging_payloads.append(
    genPayload(
        command="docker ps -a",  # usually we want to run ps -a to get failed containers in the output logs!
        description="get container health state",
        limits="1s",
        offset="200ms",
        payload_type="logs",
        target=["client", "server"],
    )
)

logging_payloads.append(
    genPayload(
        command="docker container logs plc-logic --tail 10",
        description="check client plc-logic health",
        limits="1s",
        offset="200ms",
        payload_type="logs",
    )
)

logging_payloads.append(
    genPayload(
        command="docker container logs plc-server --tail 10",
        description="check client plc-server health",
        limits="1s",
        offset="200ms",
        payload_type="logs",
    )
)

logging_payloads.append(
    genPayload(
        command="docker container logs plc-historian --tail 10",
        description="check client plc-historian health",
        limits="1s",
        offset="200ms",
        payload_type="logs",
    )
)

logging_payloads.append(
    genPayload(
        command="journalctl -n 20 --no-pager",
        description="Get the latest server logs, in case of failure",
        limits="1s",
        offset="{end_of_test_logs}s",
        payload_type="logs",
        target=["client", "server"],
    )
)
