import logging
from rich import print as rprint
from pathlib import Path

from capcon.util.payload import format_payloadIds_with_digest, genPayload
from motra.common.capcon import write_capcon_to_file
from motra.common.capcon_protocol import CAPCON, GenericPayload
from capcon.log_payload import logging_payloads


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, datefmt="%H:%M:%S")

# #############################################################################################

capcon_output_folder = Path(".") / "tmp-gen"
capcon_output_folder.resolve().mkdir(exist_ok=True)
log.info(capcon_output_folder)


flooding_payloads: list[GenericPayload] = []
flooding_payloads.append(
    genPayload(
        command="timeout 60 ping -f {target_ip}",
        description="run a flooding payload against a single IP",
        limits="65s",
        offset="500ms",
        payload_type="attack",
        target=["server"],
    )
)


# create a payload to reset the current testbed configuration
# this is required, in case the testbed crashes or we hit a timeout for the subscription services
config_payloads: list[GenericPayload] = []
config_payloads.append(
    genPayload(
        command="docker compose -f /home/motra/plc.yaml restart",
        description="restart containers ... ",
        limits="30s",
        offset="200ms",
        payload_type="config",
    )
)

# the network capture process is also a static payload.
# we try to generate pcaps for the baseline measurements and for the attacks
static_payloads: list[GenericPayload] = []
static_payloads.append(
    genPayload(
        command="timeout 60 sudo tcpdump -i enxa0cec88b1a4e -w {capconname}.pcap",
        target=["server"],
        description="archive current network interaction",
        limits="65s",
        offset="500ms",
        payload_type="capture",
    )
)

# add the currently configured logging payloads, since we always need those
static_payloads.extend(logging_payloads)

# we need some repetition for the payloads
# Generate each test X times (for starter with identical configuration)
# we can add some level of variation in the future...
repetition = 1
dynamic_payloads = flooding_payloads[:]
capture_configurations: list[CAPCON] = []
id_count = 1

# in case we have multiple ips or combinations, we need to create permutations using itertools
tartget_ip = "10.10.10.103"


for dyn_payloads in dynamic_payloads:

    # run N measurements to get a good baseline
    for i in range(0, repetition):

        nextCapConName = f"flooding_measurements_{id_count:04}"

        # create a copy of static payload list and populate the names
        payload: list[GenericPayload] = [item.model_copy() for item in static_payloads]
        payload.append(dyn_payloads.model_copy())

        # update all the runtime parameters (names, runtime in s)
        for load in payload:
            load.command = load.command.format(
                capconname=nextCapConName,
                target_ip=tartget_ip,
            )

        payload = format_payloadIds_with_digest(payload, nextCapConName)

        # we run the default configs for about one minute
        # this way we can inject the config samples easily
        newCon = CAPCON(
            CapConID=nextCapConName,
            duration="70s",
            payload=payload,
            description=f"flooding attack {nextCapConName}",
            timestamp_utc="",
        )

        capture_configurations.append(newCon)
        id_count += 1

        # every x iterations add a config reset
        if id_count % 5 == 0:
            confLoad: list[GenericPayload] = [
                item.model_copy() for item in config_payloads
            ]
            nextCapConName = nextCapConName + "_config"
            confLoad = format_payloadIds_with_digest(confLoad, nextCapConName)
            configCon = CAPCON(
                CapConID=nextCapConName,
                duration="35s",
                payload=confLoad,
                description="config reset for docker",
                timestamp_utc="",
            )
            capture_configurations.append(configCon)


# print(len(capture_configurations))

# generate the base configuration
for capcon in capture_configurations:
    # rprint(capcon)
    write_capcon_to_file(
        capcon_output_folder,
        capcon,
        capcon_name=capcon.CapConID + ".json",
        create_ID_file=False,
    )
