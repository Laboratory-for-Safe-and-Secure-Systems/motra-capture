from pathlib import Path
import logging

from motra.common import util
from motra.common.response_types import Status
from motra.common.schedule import COMMAND
from motra.workspace.workspace_configuration import ServerFileConfiguration

# this would be the module specific logger
main_log = logging.getLogger(__name__)


class MotraServerConfig:
    """
    The server side configuration class: generates a default configuration for
    logging and handles the different tests upon start.

    The server class has two main responsibilities: configuring the logger and
    setting up tests, when started. The logging is required, since we are
    attached to the fastAPI default logger per default configuration. When the
    server initially is started up or restarted, we also need to parse the
    current set of tests available, but only once. This is required to pop each
    test off the current execution stack one it has been run.

    test_configuration_location: The current Path that will be checked for test
        files. Each test inside this directory is parsed by the server on startup
        and loaded into the execution stack.

    pending_tests: This is the list of currently available tests. For the server
        this will be sent to the client test by test on each request.

    """

    test_configuration_location: Path
    test_queue: list

    def __init__(
        self,
        configuration: ServerFileConfiguration,  # TODO: add support for the server relevant stuff, logging has been moved
        workspace: dict[str, Path] = None,
    ):
        """
        The internally used configuration for the server process. Configures
        how and where the tests are loaded/parsed.

        Parameters:
            workspace (Path): A valid path to a workspace, to locate tests.

        """
        # INFO: The logging configuration needs to be done inside the FastAPI
        #       lifespan module, since this will be run as a wrapper for the
        #       server process.

        # store a reference to the ServerFileConfiguration
        server_configuration = configuration

        # setup the measurements inside workspace
        self.live_workspace = workspace["live"]
        self.archive_workspace = workspace["archive"]
        self.test_configuration_location = workspace["tests"]

        # setup tests
        # this might be extended using a external KV store like redis
        # this is the
        self.test_queue = list()

        # payload state for the current run
        self.capture_jobs: dict[str, Path] = {}
        self.schedule_units: list[COMMAND] = list()

    @property
    def live_data(self):
        return self.live_workspace

    @property
    def archive_data(self):
        return self.archive_workspace

    @property
    def jobs_active(self):
        return len(self.capture_jobs) != 0

    def add_to_active_jobslist(self, payload_id: str, payload_file: Path):
        self.capture_jobs.update({payload_id: payload_file})

    def pop_from_active_jobslist(self) -> dict[str, Path] | None:
        if len(self.capture_jobs) == 0:
            return None
        return self.capture_jobs.popitem()

    def scan_tests(self) -> list[Path]:
        """
        We collect a set of preconfigured tests to run when the server starts
        the dict containing the tests is updated once the server runs
        we then send each test once to the client and wait until we get the
        final test data
        this way we only store one set of test configurations and can run
        many different tests in succession
        """
        # scan the configured directory and return a list containing Path and testID
        self.test_queue = list(self.test_configuration_location.glob("*.json"))
        main_log.debug(
            f"Server: Found {len(self.test_queue)} tests to upload to the client ",
            extra={"data": self.test_queue},
        )

        loaded_data = util.load_json_files_into_list(self.test_queue)
        if loaded_data.status is not Status.SUCCESS:
            exit(1)

        uniqueness = util.check_id_uniqueness(
            loaded_data.payload,
            "CapConID",
        )
        if uniqueness.status is not Status.SUCCESS:
            exit(1)

        return self.test_queue

    def get_test_list(self) -> list[Path]:
        """
        Returns the current set of unscheduled tests from the server. This list
        holds the references to all tests, that were found during the initialization
        of the server application.
        """
        return self.test_queue

    def get_pending_test(self) -> Path | None:
        """
        Returns the next test, that is on the first position of the queue, without
        poping from the list.
        """
        if len(self.test_queue) == 0:
            return None

        return self.test_queue[0]

    def pop_test(self) -> Path | None:
        """
        Removes the first test from the list. Similar to list.pop(0).
        """
        if len(self.test_queue) == 0:
            return None

        return self.test_queue.pop(0)


# Create a single instance that will be shared
# This is a form of a singleton pattern.
# this is required for the fastAPI configuration to handle external dependencies
_server_instance = None


# This is our dependency provider function for FastAPI
def get_server_config() -> MotraServerConfig:
    """Dependency to provide the application configuration."""
    global _server_instance
    if _server_instance is None:
        _server_instance = MotraServerConfig()
    return _server_instance


# This can be used to create non default configurations
def set_server_config(config) -> MotraServerConfig:
    """
    Create a non default server configuration. This will only update the
    server_instance, if it is None!

    """
    global _server_instance
    if _server_instance is None:
        _server_instance = config
    else:
        raise ValueError("Cannot overwrite existing server configuration.")
    return _server_instance
