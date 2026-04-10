from capcon.util.payload import (
    format_payloadIds_with_digest,
    genPayload,
)
from capcon.util.systemd_time import parse_systemd_timespan

from rich import print as rprint
from pathlib import Path
import logging

from motra.common.capcon import write_capcon_to_file
from motra.common.capcon_protocol import CAPCON, GenericPayload
from capcon.log_payload import logging_payloads

from capcon.perf_stat import default_options, genCommand

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, datefmt="%H:%M:%S")

# #############################################################################################

capcon_output_folder = Path(".") / "tmp-gen" / "recon"
capcon_output_folder.resolve().mkdir(parents=True, exist_ok=True)
log.info(capcon_output_folder)


nmap_payloads: list[GenericPayload] = []


# default takes around 16s for runtime
nmap_payloads.append(
    genPayload(
        command="nmap -n -A -e end0 -oG capcon{target_ip}",
        description="default settings for nmap with default timeout",
        limits="25s",
        offset="500ms",
        payload_type="attack",
        target=["server"],
    )
)

# get different timing ranges or levels of aggressiveness
# T0 takes insanely long, the default startup is like 5 minutes
# -A -T5 ca 1.2 secs for a single ip
# -A -T5 175 secs for a 24 subnet
# -A -T3 ca about 1.1 secs for a single ip
# aggressive timing does not work well with scripted setups.
# for i in range(0, 5):
#     nmap_payloads.append(
#         genPayload(
#             command=f"nmap -n -A -T{i} -oG capcon\u007btarget_ip\u007d",
#             description="nmap 1",
#             limits="65s",
#             offset="500ms",
#             payload_type="attack",
#         )
#     )

# 405s for a single IP
nmap_payloads.append(
    genPayload(
        command=f"nmap -n -A -T2 -e end0 -oG capcon\u007btarget_ip\u007d",
        description="stealthy scan using default values but -T2",
        limits="505s",
        offset="500ms",
        payload_type="attack",
        target=["server"],
    )
)

# 1400 secs for a single ip
# TODO: we might need to run these tests isolated
# this test is still broken (also the systemd limit does not seem to be working in this instance)
# this runtime will create config issues with the OPC UA timeout, unless we reconfigure the servers
nmap_payloads.append(
    genPayload(
        command="nmap -n -sU -Pn -e end0 -oG capcon{target_ip}",
        description="UDP scan with default options",
        limits="1400s",
        offset="500ms",
        payload_type="attack",
        target=["server"],
    )
)

# idle scan does not work in our current setup
# nmap_payloads.append(
#     genPayload(
#         command="nmap -n  -sI -Pn -oG capcon{target_ip}",
#         description="nmap 1",
#         limits="65s",
#         offset="500ms",
#         payload_type="attack",
#     )
# )

# 1.8 secs for single IP
nmap_payloads.append(
    genPayload(
        command="nmap -n -sN -Pn -e end0 -oG capcon{target_ip}",
        description="TCP Null scan with default options",
        limits="6s",
        offset="500ms",
        payload_type="attack",
        target=["server"],
    )
)

# 1.8 secs for single IP
nmap_payloads.append(
    genPayload(
        command="nmap -n -sF -Pn -e end0 -oG capcon{target_ip}",
        description="TCP FIN scan with default options",
        limits="6s",
        offset="500ms",
        payload_type="attack",
        target=["server"],
    )
)

# minor changes with T4 and T3
# 1.8 secs for single IP
nmap_payloads.append(
    genPayload(
        command="nmap -n -sX -Pn -e end0 -oG capcon{target_ip}",
        description="TCP XMAS scan with default options",
        limits="6s",
        offset="500ms",
        payload_type="attack",
        target=["server"],
    )
)

# about 0.5 secs for a single IP on T3
nmap_payloads.append(
    genPayload(
        command="nmap -n -PA -e end0 -oG capcon{target_ip}",
        description="TCP ACK Ping scan with default options",
        limits="3s",
        offset="500ms",
        payload_type="attack",
        target=["server"],
    )
)

# detections require more time
# about 4 secs for a single ip
nmap_payloads.append(
    genPayload(
        command="nmap -sX -O -e end0 -sV -oG capcon{target_ip}",
        description="testing with OS detection",
        limits="6s",
        offset="500ms",
        payload_type="attack",
        target=["server"],
    )
)

# default script option takes about 4s for single ip
nmap_payloads.append(
    genPayload(
        command="nmap -sC -O -e end0 -sV -oG capcon{target_ip}",
        description="default scripting options with -sC ",
        limits="6s",
        offset="500ms",
        payload_type="attack",
        target=["server"],
    )
)

# about 55s for a single IP
nmap_payloads.append(
    genPayload(
        command='nmap --script "default or safe" -e end0 -O -sV -oG capcon{target_ip}',
        description="nmap scripts: default or safe",
        limits="65s",
        offset="500ms",
        payload_type="attack",
        target=["server"],
    )
)

# about 26.5 secs for a single IP
nmap_payloads.append(
    genPayload(
        command='nmap --script "vuln" -e end0 -O -sV -oG capcon{target_ip}',
        description="nmap scripts: vuln scan",
        limits="35s",
        offset="500ms",
        payload_type="attack",
        target=["server"],
    )
)

# 26s for a single IP
nmap_payloads.append(
    genPayload(
        command='nmap --script "dos" -e end0 -O -sV -oG capcon{target_ip}',
        description="nmap scripts: dos scan",
        limits="35s",
        offset="500ms",
        payload_type="attack",
        target=["server"],
    )
)

# ssh uses some timeouts to block specific connections. depending on the current configuration this might need some
# changes to allow for scanning in multiple iterations
nmap_payloads.append(
    genPayload(
        command="nmap -T5 -p 22 --script ssh-brute -oG capcon--script-args userdb=users.lst,passdb=pass.lst --script-args ssh-brute.timeout=4s {target_ip}",
        description="nmap 1",
        limits="305s",
        offset="500ms",
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
        command="sudo tcpdump -i enxa0cec88b1a4e -w {capconname}.pcap",
        target=["server"],
        description="archive current network interaction",
        limits="{tcpdump_runtime}s",
        offset="400ms",
        payload_type="capture",
    )
)

static_payloads.append(
    genPayload(
        command=genCommand(default_options, "{perf_runtime}"),
        target=["client"],
        description="perf stat default",
        limits="{perf_runtime}s",
        offset="500ms",
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


# we need some repetition for the payloads
# Generate each test X times (for starter with identical configuration)
# we can add some level of variation in the future...
repetition = 1
dynamic_payloads = nmap_payloads[:]
capture_configurations: list[CAPCON] = []
id_count = 1


# in case we have multiple ips or combinations, we need to create permutations using itertools
tartget_ip = "10.10.10.103"


for dyn_payloads in dynamic_payloads:

    # run N measurements to get a good baseline
    for _ in range(0, repetition):

        nextCapConName = f"recon_measurements_{id_count:04}"

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
                perf_runtime=str(upper_runtime),
            )
            load.limits = load.limits.format(
                tcpdump_runtime=str(upper_runtime + 1),  # actual limit
                perf_runtime=str(upper_runtime + 1),
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
