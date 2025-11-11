import time
import json
from statemachine import StateMachine, State

from motra.common import util
from motra.common.capcon import (
    load_capcon_from_file,
    write_capcon_to_file,
    write_payload_to_file,
)
from motra.common.capcon_protocol import *
from motra.common.response_types import Status

from motra.common.archive import (
    clean_workspace,
    create_archive,
)
from motra.common.schedule import (
    COMMAND,
    execute_scheduler_template,
    generate_scheduler_template,
    schedule_client_process,
    schedule_capture_process,
)

from motra.client import requests
from motra.client.client_connection import ClientConnection
from motra.client.configuration import MotraClientConfig


logger = logging.getLogger(__name__)

# TODO: this needs to move!
test_command = ""


class MeasurementClient(StateMachine):

    # disable code formatting to prevent breaking the code generator for the state machine/transitions
    # fmt: off
    disconnected = State(initial=True)
    connecting = State()
    connected = State()
    upload_data_available = State()
    preparing_ready_for_test = State()
    offline_testing = State(final=True)

    connect = disconnected.to(connecting)
    connection_successfull = connecting.to(connected)
    start_upload = connected.to(upload_data_available) | upload_data_available.to(upload_data_available)
    upload_complete = upload_data_available.to(preparing_ready_for_test) | connected.to(preparing_ready_for_test)
    transition_await_final_test_trigger = preparing_ready_for_test.to(offline_testing)
    # fmt: on

    # error handling
    connection_failed = connecting.to(disconnected) | connected.to(disconnected)

    def __init__(
        self,
        clientConfig: MotraClientConfig,
        clientConnection: ClientConnection,
        workspace: dict,
    ):
        self.config = clientConfig
        self.connection = clientConnection
        self.pending_files = list()
        self.current_captureConfiguration: str
        self.workspace = workspace

        # if we store all payloads, we need to prep all systemd units
        # starting with the main client unit and then all transient units
        # required for starting the different payloads...
        self.schedule_units: list[COMMAND] = list()

        # the default number should be 3 for live, staged, archives
        if len(workspace.keys()) != 3:
            raise ValueError("wrong number of keys for workspace")

        # setup the main state machine, so we can query/upload/receive CapCons.
        super().__init__()

    # #################         Event Handlers      #####################

    @disconnected.enter
    async def client_idle(self):

        wait_time = self.config.backoff()
        logger.info(
            f"Entered DISCONNECTED state. Will try to connect in {wait_time}s.",
        )
        time.sleep(wait_time)

    @connect.on
    async def issue_connection_request(self):
        ccon = self.connection
        status = await ccon.connect()
        if status.status != Status.SUCCESS:
            # silently stop here, we need to check in CONNECTING, if we are fine
            # otherwise this will break the state machine
            await self.connection_failed()
            return

        request = requests.parse_CLIENT_HELLO()
        if request.status is not Status.SUCCESS:
            exit(1)

        json_to_send = request.payload.model_dump_json(indent=2)
        await ccon.send(json_to_send)

    @connecting.enter
    async def wait_for_server_hello(self):
        # if the initial connection fails, we will not get a valid socket
        # in this case emit a connection request event and restart the state machine
        conman = self.connection
        if not conman.is_connected():
            await self.connect()
            return

        logger.info("Entered CONNECTING state. Waiting for SERVER_HELLO ...")
        data = await conman.receive()
        if data.status != Status.SUCCESS:
            exit(1)

        unsanitized_data = json.loads(data.payload)  # needs derserialize before use
        parsed_data = util.validate(model=SERVER_HELLO, data=unsanitized_data)

        # we failed to load the json stream into memory
        if parsed_data is None:
            exit(1)

        logger.debug(
            "Received SERVER_HELLO from Server",
            extra={"data": parsed_data.model_dump()},
        )

        logger.info("Connection Successfull")
        await self.connection_successfull()  # CONNECTING >> QUERY DATA

    @connected.enter
    async def checking_files_for_upload(self):

        # before uploading the files, we need to parse the current test:
        last_capture = load_capcon_from_file(self.workspace["live"])

        # Archive the last test, if one is available
        if last_capture is not None:
            logger.info("Generating new zip archive for previous capture run.")
            create_archive(
                archive_name=last_capture.CapConID,
                source_directory=self.workspace["live"],
                target_directory=self.workspace["staging"],
                run_post_archive_checks=True,
            )
            clean_workspace(self.workspace["live"])

        logger.info("Determining files for upload...")

        # are there any local files present?
        # if yes create a map and prepare upload
        self.pending_files = list(self.workspace["staging"].glob("*"))
        if not self.pending_files:
            logger.info("No pending files for upload...")
            await self.upload_complete()  # ------> GOTO >> request_new_test_from_server
            return

        # try to upload the first file archive
        await self.start_upload()  # ------> GOTO >> upload_file_to_server

    @start_upload.on
    async def upload_file_to_server(self):
        conman = self.connection

        logger.info("Uploading file to server...")
        next_file = self.pending_files[0]
        self.pending_files.pop(0)
        if next_file == None:
            logger.info("File descriptior cannot be empty")
            exit(1)

        request = requests.parse_REQUEST_UPLOAD(next_file)

        if request.status is not Status.SUCCESS:
            exit(1)

        json_to_send = request.payload.model_dump_json(indent=2)
        await conman.send(json_to_send)

    @upload_data_available.enter
    async def handle_UPLOAD_COMPLETE(self):

        conman = self.connection
        logger.info("Started uploading file...")

        # server acknowledged the file upload
        # we should be safe to remove the archive from our storage
        # or just mark the archive to be removed for now
        data = await conman.receive()
        unsanitized_data = json.loads(data.payload)  # needs derserialize before use
        parsed_data = util.validate(
            model=UPLOAD_COMPLETE,
            data=unsanitized_data,
        )

        # the file name is sent back to ack the last archive
        # we can use the archive name in this case to move the file from
        # staging to done
        if parsed_data.file_name:
            source = self.workspace["staging"] / parsed_data.file_name
            dest = self.workspace["archived"] / parsed_data.file_name
            util.move_file(source, dest)

        # ... if there are more files to upload
        if len(self.pending_files) != 0:
            await self.start_upload()
            return

        logger.info("Upload of file(s) complete...")
        await self.upload_complete()  # ------> GOTO >> request_new_capcon_from_server

    @upload_complete.on
    async def request_new_capcon_from_server(self):
        conman = self.connection
        logger.info("Requesting new test from server...")
        request = requests.parse_REQUEST_CAPCON()

        if request.status is not Status.SUCCESS:
            exit(1)

        json_to_send = request.payload.model_dump_json(indent=2)
        await conman.send(json_to_send)

    @preparing_ready_for_test.enter
    async def handle_CAPCON(self):

        logger.info("Waiting for new test from server...")
        conman = self.connection
        data = await conman.receive()
        if data.payload is None:
            raise RuntimeError(f"Receiving failed with: {data.status}")

        unsanitized_data = json.loads(data.payload)  # needs derserialize before use
        parsed_data = util.validate(
            model=CAPCON,
            data=unsanitized_data,
        )

        # in this case we executed all available tests from the server and we can
        # stop all exection. If we already sent the previous test and receive an
        # empty response, there will be no additional measurements required
        # Important: kill the active session, so we can close gracefully!
        if parsed_data.CapConID == "":
            logger.info("Received empty test, stopping...")
            await conman.disconnect(reason="Tests finished, closing gracefully")
            exit(0)

        # store the current ID for the next state here
        # we should be able to put this as a parameter into the statemachine somehow
        self.current_captureConfiguration = parsed_data.CapConID
        logger.info(f"Received {parsed_data.CapConID}...")

        # store the current capture configuration to disk for the next run
        write_capcon_to_file(
            self.workspace["live"],
            parsed_data,
        )

        # next we need to parse the payload
        # is there a case where we do not have any?
        client_id = self.config.ClientId
        active_payloads: list[GenericPayload] = list()
        if parsed_data.payload:
            for payload in parsed_data.payload:
                if client_id in payload.target:
                    active_payloads.append(payload)
                    pid = payload.payload_id
                    current_job = self.workspace["live"] / f"{pid}.json"
                    write_payload_to_file(current_job, payload=payload)

        client_unit = generate_scheduler_template(
            "motra-client",
            current_id=parsed_data.CapConID,
            start_time_delta=parsed_data.duration,
            template_unit=True,
        )

        self.schedule_units.append(client_unit)

        if active_payloads:
            for payload in active_payloads:
                payload_unit = generate_scheduler_template(
                    "motra-client-mexec",
                    current_id=payload.payload_id,
                    start_time_delta="3s",
                    template_unit=True,
                )
                self.schedule_units.append(payload_unit)

        # When the final trigger is received, you call:
        await self.transition_await_final_test_trigger()

    @transition_await_final_test_trigger.on
    async def request_server_test_trigger(self):
        logger.info("Requesting final trigger from server...")
        conman = self.connection
        request = requests.parse_ACK_CAPCON(
            current_test_id=self.current_captureConfiguration,
        )

        if request.status is not Status.SUCCESS:
            exit(1)

        json_to_send = request.payload.model_dump_json(indent=2)
        await conman.send(json_to_send)

    @offline_testing.enter
    async def kill_and_disown_client(self):
        logger.info("Waiting for execution trigger")
        conman = self.connection
        data = await conman.receive()
        unsanitized_data = json.loads(data.payload)  # needs derserialize before use
        parsed_data = util.validate(model=EXECUTE_CAPCON, data=unsanitized_data)

        if self.current_captureConfiguration != parsed_data.CapConID:
            logger.error("Current and Received test CapConIDs do not match")
            exit(1)

        # run all commands
        for command in self.schedule_units:
            execute_scheduler_template(command)

        # we run the commands before closing the handshake, since this blocks.
        # we need to add some offset to all commands when running this
        await conman.disconnect()
        logger.info("Entered OFFLINE_TESTING state. Killing the Measurement Client")

        # launch_and_disown_capture_task()
        logger.info("Client is now offline. State machine has finished.")
