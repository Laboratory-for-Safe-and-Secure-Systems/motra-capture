import logging
from pathlib import Path

from rich import print as rprint

from capcon.log_payload import logging_payloads
from capcon.util.systemd_time import parse_systemd_timespan
from motra.common.capcon import write_capcon_to_file
from motra.common.capcon_protocol import CAPCON
from capcon.util.payload import (
    genPayload,
    format_payloadIds_with_digest,
)
from motra.common.capcon_protocol import GenericPayload


# To be able to use Sliver correctly, we need to setup a server on the attacker node
# and the required implants before any test.
#
# sliver server is started with systemd:
# sudo systemctl start sliver-server

# payload would be to run a implant on the client side
# tell mexec to run a generated implant on the client node:
# command="ARM64_SESSION"
# command="ARM64_BEACON"

# cleanup:
# remove session or beacon:
# ... (we need to fully clean any configuration, otherwise the next runs will be broken)
# stop the server:
# sudo systemctl stop sliver-server


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, datefmt="%H:%M:%S")

# #############################################################################################

capcon_output_folder = Path(".") / "tmp-gen" / "c2"
capcon_output_folder.resolve().mkdir(parents=True, exist_ok=True)
log.info(capcon_output_folder)


# IMPORTANT: these are NOT run as single dynamic payloads, these need to be run in one session!
c2_payloads: list[GenericPayload] = []
c2_payloads.append(
    genPayload(
        command="sudo systemctl start sliver",
        target=["server"],
        description="setup the sliver server to accept client connections and sessions",
        limits="5s",
        offset="2s",
        payload_type="attack",
    )
)

# we install the payloads into /usr/local/bin
# therefore all required payloads should be system callable
# ARM64_SESSION, ARM64_BEACON
# c2_payloads.append(
#     genPayload(
#         command="/opt/sliver/ARM64_SESSION",
#         target=["client"],
#         description="Start a client session for testing",
#         limits="30s",
#         offset="5s",
#         payload_type="attack",
#     )
# )

# runuser is required, bc motra-server shedules as root user
# c2_payloads.append(
#     genPayload(
#         command="runuser -l motra -c 'run_session_info'",
#         target=["server"],
#         description="test the session info command",
#         limits="5s",
#         offset="12s",
#         payload_type="attack",
#     )
# )

# c2_payloads.append(
#     genPayload(
#         command="runuser -l motra -c 'run_session_ipa'",
#         target=["server"],
#         description="test the session payload command",
#         limits="5s",
#         offset="14s",
#         payload_type="attack",
#     )
# )

c2_payloads.append(
    genPayload(
        command="/opt/sliver/ARM64_BEACON",
        target=["client"],
        description="Start a client session for testing",
        limits="200s",
        offset="5s",
        payload_type="attack",
    )
)

# runuser is required, bc motra-server shedules as root user
c2_payloads.append(
    genPayload(
        command="runuser -l motra -c 'run_beacon_info'",
        target=["server"],
        description="test the session info command",
        limits="5s",
        offset="12s",
        payload_type="attack",
    )
)

c2_payloads.append(
    genPayload(
        command="runuser -l motra -c 'run_beacon_payload'",
        target=["server"],
        description="test the session payload command",
        limits="5s",
        offset="14s",
        payload_type="attack",
    )
)

c2_payloads.append(
    genPayload(
        command="runuser -l motra -c 'kill_active_beacon'",
        target=["server"],
        description="test the session payload command",
        limits="10s",
        offset="170s",
        payload_type="attack",
    )
)


c2_payloads.append(
    genPayload(
        command="sudo systemctl stop sliver",
        target=["server"],
        description="setup the sliver server to accept client connections and sessions",
        limits="5s",
        offset="188s",
        payload_type="attack",
    )
)


# -------------------------------------------------------------------------------- #
# configuration and capture payloads


# create a payload to reset the current testbed configuration
# this is required, in case the testbed crashes or we hit a timeout for the
# subscription services
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
    command="sudo tcpdump -i enxa0cec88b1a4e -w {capconname}.pcap",
    target=["server"],
    description="archive current network interaction",
    limits="{tcpdump_runtime}s",
    offset="500ms",
    payload_type="capture",
)

# -------------------------------------------------------------------------------- #

# configure the default options for all testcases
# we can use itertools.product to create a mixed set of testing options for
# different use cases. If we have a set of options run product on the lists of
# elements, then generate and update all payloads using .format().

# none needed

# -------------------------------------------------------------------------------- #


# create a list of default payloads
static_payloads: list[GenericPayload] = [item.model_copy() for item in logging_payloads]
static_payloads.append(capture_payload)

repetition = 1
dynamic_payloads = c2_payloads[:]  # shallow copy
mitm_configurations: list[CAPCON] = []
id_count = 1


# run N measurements to get a good baseline
for _ in range(0, repetition):

    nextCapConName = f"command_control_payload_{id_count:04}"

    # create a copy of static payload list and populate the names
    payload = [item.model_copy() for item in static_payloads]
    added_payloads = [item.model_copy() for item in dynamic_payloads]
    payload.extend(added_payloads)

    # the dyn. models are required to set the upper runtime limit
    # add 1s as margin, in case some payload uses a subsecond interval
    # this will just round up the runtime for the tcpdump process to the next full second
    # upper_runtime = int(parse_systemd_timespan(dynamic_payloads.limits))
    # upper_runtime += 1
    upper_runtime = 220

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
        description=f"run C2 configurations for testing",
        timestamp_utc="",
    )
    CAPCON.model_validate(newCon.model_dump())
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
    CAPCON.model_validate(configCon.model_dump())
    mitm_configurations.append(configCon)


# generate the base configuration
for capcon in mitm_configurations:
    # rprint(capcon)
    write_capcon_to_file(
        capcon_output_folder,
        capcon,
        capcon_name=capcon.CapConID + ".json",
        create_ID_file=False,
    )
