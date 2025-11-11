import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

# we may want to check the server side configuration of the measurement folders
from motra.server.configuration import get_server_config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's startup and shutdown events.
    """
    # --- Code to run ON STARTUP ---
    config = get_server_config()
    logger.info("Motra Server Startup: Initializing testing infrastructure...")
    logger.info(
        f"Selected location for test data: {config.test_configuration_location}"
    )
    tests = config.scan_tests()
    logger.info(f"Found {len(tests)} test(s) in the configured directory.")

    # this is suspended until fastAPI stops
    yield

    # --- Code to run ON SHUTDOWN ---
    # This code will execute after the server receives a shutdown signal (e.g., Ctrl+C)
    logger.info("Motra Server Shutdown: Cleaning up resources...")

    # tbd

    logger.info("--- Server has shut down. ---")
