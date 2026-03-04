from capcon.payload import genPayload, GenericPayload

from itertools import product
import logging

from rich import print as rprint

from pathlib import Path
from capcon.payload import format_payload, genPayload

from motra.common.capcon import write_capcon_to_file
from motra.common.capcon_protocol import CAPCON
from capcon.log_payload import logging_payloads

# general usage /motra/remote-exploit/claroty-framework$ python3 main.py dotnetstd 172.17.0.2 4840 / sanity

testing_functions = [
    "sanity",
    "certificate_inf_chain_loop",
    "chunk_flood",
    "open_multiple_secure_channels",
    "unlimited_persistent_subscriptions",
    "unlimited_condition_refresh",
]

server_type = [
    "dotnetstd",
    "open62541",
    "rust",
    "node-opcua",
    "opcua-python",
]

dest_ip = ["10.10.10.103"]


opc_generic_payload = genPayload(
    command="timeout 200 python3 main.py {server_type} {target_ip} 4840 /KRITIS3M {function}",
    description="claroty OPC for {server_type}",
    limits="200s",
    offset="500ms",
    payload_type="attack",
)

opc_payloads: list[GenericPayload] = []

for item_a, item_b, item_c in product(server_type, dest_ip, testing_functions):

    # update format strings
    opc_load = opc_generic_payload.model_copy()
    opc_load.command = opc_load.command.format(
        server_type=item_a,
        target_ip=item_b,
        function=item_c,
    )
    opc_load.description = opc_load.description.format(
        server_type=item_a,
        target_ip=item_b,
        function=item_c,
    )
    opc_payloads.append(opc_load)  # these should be copies ready for formatting


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, datefmt="%H:%M:%S")

# #############################################################################################

capcon_output_folder = Path(".") / "tmp-gen"
capcon_output_folder.resolve().mkdir(exist_ok=True)
log.info(capcon_output_folder)


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
        command="timeout 200 sudo tcpdump -i enxa0cec88b1a4e -w {capconname}.pcap",
        target=[
            "server",
        ],
        description="archive current network interaction",
        limits="205s",
        offset="500ms",
        payload_type="capture",
    )
)

# add the currently configured logging payloads, since we always need those
static_payloads.extend(logging_payloads)

# we need some repetition for the payloads
# Generate each test X times (for starter with identical configuration)
# we can add some level of variation in the future...
repetition = 5
dynamic_payloads = opc_payloads[:]
opc_configurations: list[CAPCON] = []
id_count = 1

for dyn_payloads in dynamic_payloads:

    # run N measurements to get a good baseline
    for i in range(0, repetition):

        nextCapConName = f"opc_tampering_measurements_{id_count:04}"

        # create a copy of static payload list and populate the names
        payload = [item.model_copy() for item in static_payloads]
        for load in payload:
            load.command = load.command.format(capconname=nextCapConName)

        # create a list of payloads and update payload IDs
        payload.append(dyn_payloads.model_copy())
        payload = format_payload(payload, nextCapConName)

        # we run the default configs for about one minute
        # this way we can inject the config samples easily
        newCon = CAPCON(
            CapConID=nextCapConName,
            duration="210s",
            payload=payload,
            description=f"opc claroty interactions for {dyn_payloads.description}",
            timestamp_utc="",
        )

        opc_configurations.append(newCon)
        id_count += 1

        # every 20 iterations add a config reset
        if id_count % 5 == 0:
            confLoad: list[GenericPayload] = [
                item.model_copy() for item in config_payloads
            ]
            nextCapConName = nextCapConName + "_config"
            confLoad = format_payload(confLoad, nextCapConName)
            configCon = CAPCON(
                CapConID=nextCapConName,
                duration="65s",
                payload=confLoad,
                description="config reset for docker",
                timestamp_utc="",
            )
            opc_configurations.append(configCon)


# print(len(capture_configurations))

# generate the base configuration
for capcon in opc_configurations:
    # rprint(capcon)
    write_capcon_to_file(
        capcon_output_folder,
        capcon,
        capcon_name=capcon.CapConID + ".json",
        create_ID_file=False,
    )
