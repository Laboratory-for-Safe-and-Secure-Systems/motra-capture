#!/bin/bash

/opt/poetry/bin/poetry run python3 baseline_perf.py
/opt/poetry/bin/poetry run python3 opc.py 
/opt/poetry/bin/poetry run python3 bruteforce.py
/opt/poetry/bin/poetry run python3 capcontrol.py
/opt/poetry/bin/poetry run python3 ettercap.py
/opt/poetry/bin/poetry run python3 flood.py
/opt/poetry/bin/poetry run python3 nmap.py