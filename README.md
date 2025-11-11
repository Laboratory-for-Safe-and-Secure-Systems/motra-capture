# MOTRA-Capture

MOTRA Capture is an automation framework that allows to create measurement configurations based on a client server architecture, that can be run inside the MOTRA testbed. The goal is to automate the measurement process together with sample attacks to create clean and repetetive datasets for research purposes.


This is an early release of our measurment and automation framework.

Setup and installation can be done using python and the provided project files: 

```bash
pipx install
# or using poetry
eval $(/opt/poetry/bin/poetry env activate) 
```

The main usage is by starting the motra executable, that will be installed when 
using poetry or pipx. From there a new workspace needs to be setup between the
client and the server. MOTRA-capture uses systemd for scheduling events on the 
client and server side and can be used to run measurements and attacks on our 
MOTRA-testbed. Before starting a new measurement, the client and server workspace
environment needs to be set up. For this run `motra workspace client/server`

```
(motra-py3.11) ~/capture $ motra

 Usage: motra [OPTIONS] COMMAND [ARGS]...

╭─ Options ─────────────────────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.                       │
│ --show-completion             Show completion for the current shell, to copy it or customize  │
│                               the installation.                                               │
│ --help                        Show this message and exit.                                     │
╰───────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ────────────────────────────────────────────────────────────────────────────────────╮
│ workspace   Workspace configuration for setting up the systemd scheduler.                     │
│ client      Start a Client for generating test data for a device.                             │
│ server      Run a local measurement server to orchestrate a testbed.                          │
│ gentest                                                                                       │
│ mexec       Execute a capcon payload using the configured environment                         │
╰───────────────────────────────────────────────────────────────────────────────────────────────╯
```

The main task of the client-server architecture is to schedule different types of 
tasks (attacks, measurement, configuration scripts) to be run on the server and 
the client side on a predetermined trigger from the server, given, that the 
client application will be completely terminated during the active measurement 
window. The goal here is to have no process active on a measurement target system
during an active pentest. Therefore the scheduling process will use systemd for 
provided payloads (attacks, measurements, configurations) to run the intended 
tasks at a given time, using a common trigger event, as well as schedule the next 
execution of the client application after the next measurement has been completed 
using a timeout option. Once the trigger from the server has been received, the 
client application will schedule all received tasks (attacks, measurements, 
configurations), the next client process and will then terminate itself before the
measurement starts.

For normal use, the server has two roles: the coordination of measuremnts during 
a normal test run and execution of any attacks on the current testbed. 
The client receives each test at a time and executes the payload at a specific 
offset, after reading the trigger command from the server. 

This effectively creates a remote event driven scheduler, that can be used to 
run measurement, configuration or attack tasks on the client or the server given
a fixed configuration in JSON format that will be sent before each measurement 
run.

Currently the server is started using a set of these capture configurations 
(CapCon) located inside the configured server environment. Once the server has 
found valid configuration files for CapCons, the client can request each test 
at a time, when connecting to the server.
After a single CapCon has been sent to the client application, the client will
terminate the connection when receiving the execution trigger from the server. 
Once the CapCon measurement is done, the client will reconnect to the server, uploading any
files created during the measurement process as stated in the last CapCon.