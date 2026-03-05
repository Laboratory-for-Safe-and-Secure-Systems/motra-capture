import hashlib

from capcon.systemd_time import parse_systemd_timespan
from motra.common.capcon_protocol import GenericPayload


def genPayload(
    command: str,
    description: str,
    limits: str,
    offset: str,
    payload_type: str = "other",
    target: list[str] = [
        "client",
    ],
) -> GenericPayload:

    return GenericPayload(
        payload_type=payload_type,
        payload_id="",
        target=target,
        setup="",
        command=command,
        teardown="",
        description=description,
        limits=limits,
        offset=offset,
        timestamp_utc="",
    )


def format_payloadIds_with_digest(
    payloads: list[GenericPayload],
    capConID: str,
) -> list[GenericPayload]:
    """
    parse a list of payloads and update the payload id to use correct numbering and embed the payload name hash digest as a trailer

    the trailer serves as a key that is uniquely bound to the capcon name by a shorter hash
    using the trailer with journalctl -u *hash* payloads for specific capture configurations can be filtered
    """

    # this is to identify all ids in the future
    # we use the first 8 digits from the digest of capcon
    hasher = hashlib.sha256()
    hasher.update(capConID.encode("utf-8"))
    payloadHashId = hasher.hexdigest()[:8]

    load_count = 1
    for payload in payloads:
        payload.payload_id = (
            payload.payload_type[0:3] + f"{load_count:03}-" + payloadHashId
        )
        load_count += 1

    return payloads


def get_max_runtime_limit(
    payloads: list[GenericPayload],
) -> GenericPayload:
    """
    parse a list of payloads and retrieve the payload with upper runtime limit
    """
    max_runtime = max(payloads, key=lambda load: parse_systemd_timespan(load.limits))
    return max_runtime
