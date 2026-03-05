from capcon.payload import (
    format_payloadIds_with_digest,
    genPayload,
    GenericPayload,
    get_max_runtime_limit,
)
from capcon.systemd_time import format_systemd_timespan, parse_systemd_timespan

from rich import print as rprint
from pathlib import Path
import logging

from motra.common.capcon import write_capcon_to_file
from motra.common.capcon_protocol import CAPCON, GenericPayload
from capcon.log_payload import logging_payloads


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, datefmt="%H:%M:%S")

# #############################################################################################


# hydra -l admin -p admin 10.10.100.83 -s 8000 http-get
# hydra -L seclists/dmiessler-SecLists/Usernames/Names/names.txt  -P seclists/dmiessler-SecLists/Passwords/Common-Credentials/top-passwords-shortlist.txt 10.10.100.83 ssh

bforce_payloads: list[GenericPayload] = []
bforce_payloads.append(
    genPayload(
        command="timeout 300 hydra -L {username_list} -P {password_list} {target_ip} -s 22 ssh ",
        description="perform a bruteforce attack against local SSH service",
        limits="300s",
        offset="500ms",
        payload_type="attack",
        target=["server"],
    )
)

# we need to setup a basic postgres instance for testing
bforce_payloads.append(
    genPayload(
        command="timeout 300 hydra -L {username_list} -P {password_list} {target_ip} -s 5432 postgres ",
        description="perform a bruteforce attack against local testing database",
        limits="300s",
        offset="200ms",
        payload_type="attack",
        target=["server"],
    )
)


# ------------------------------------- payload end -----------------------------------------------

# add all the static payloads
# since we add custom runtimes for each payload in this case, we will need to capture/format the runtime for tcpdump later
static_payloads: list[GenericPayload] = []
static_payloads.append(
    genPayload(
        command="timeout {tcpdump_runtime}s sudo tcpdump -i enxa0cec88b1a4e -w {capconname}.pcap",
        target=["server"],
        description="archive current network interaction",
        limits="{tcpdump_runtime}s",
        offset="400ms",
        payload_type="capture",
    )
)

# create a payload to reset the current testbed configuration
# this is required, in case the testbed crashes or we hit a timeout for the subscription services
config_payloads: list[GenericPayload] = []
config_payloads.append(
    genPayload(
        command="docker compose -f /home/motra/plc.yaml restart",
        description="restart containers ... ",
        target=["client"],
        limits="30s",
        offset="200ms",
        payload_type="config",
    )
)

# default payloads for creating device logs
static_payloads.extend(logging_payloads)

# rprint(static_payloads)
# print(payload.model_dump_json(indent=2))


capcon_output_folder = Path(".") / "tmp-gen"
capcon_output_folder.resolve().mkdir(exist_ok=True)
log.info(capcon_output_folder)


# we need some repetition for the payloads
# Generate each test X times (for starter with identical configuration)
# we can add some level of variation in the future...
repetition = 1
dynamic_payloads = bforce_payloads[:]
capture_configurations: list[CAPCON] = []
id_count = 1


# in case we have multiple ips or combinations, we need to create permutations using itertools
tartget_ip = "10.10.10.103"
# TODO: these are tbd, either install them directly or reuse the container setup
name_lists = "seclists/dmiessler-SecLists/Usernames/Names/names.txt"
pw_lists = "seclists/dmiessler-SecLists/Passwords/Common-Credentials/top-passwords-shortlist.txt "


# for item_a, item_b, item_c in product(server_type, dest_ip, testing_functions):
#  ...

for dyn_payloads in dynamic_payloads:

    # run N measurements to get a good baseline
    for _ in range(0, repetition):

        nextCapConName = f"bruteforce_measurements_{id_count:04}"

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
                target_ip=tartget_ip,
                username_list=name_lists,
                password_list=pw_lists,
            )
            load.limits = load.limits.format(
                tcpdump_runtime=str(upper_runtime + 1),  # actual limit
            )

        payload = format_payloadIds_with_digest(payload, nextCapConName)

        # we run the default configs for about one minute
        # this way we can inject the config samples easily
        newCon = CAPCON(
            CapConID=nextCapConName,
            duration=str(upper_runtime + 5) + "s",
            payload=payload,
            description="recon measurement",
            timestamp_utc="",
        )

        capture_configurations.append(newCon)
        id_count += 1

        # every x iterations add a config reset
        # for the nmap modules we need to reconfigure more often, since we have more long running scans
        if id_count % 3 == 0:
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
