import logging
from logging.handlers import RotatingFileHandler

from motra.logging.log_config import (
    configure_consoleNoTraceback_logger,
    configure_contextfile_logger,
)


def client_defaultConsoleLogger(loglevel: str) -> None:
    # setup the global log level
    level = getattr(logging, loglevel.upper())

    # remove the default global loghandler
    logging.basicConfig(level=level, datefmt="%H:%M:%S")
    logging.getLogger("").removeHandler(logging.getLogger("").handlers[0])

    # setup custom handlers downstream
    clilogger = logging.getLogger("motra.cli")
    configure_consoleNoTraceback_logger(clilogger, "CLI", loglevel=level)

    commonlogger = logging.getLogger("motra.common")
    configure_consoleNoTraceback_logger(commonlogger, "Client-Common", loglevel=level)

    workspacelogger = logging.getLogger("motra.workspace")
    configure_consoleNoTraceback_logger(workspacelogger, "Client-WS", loglevel=level)

    clientlogger = logging.getLogger("motra.client")
    configure_consoleNoTraceback_logger(clientlogger, "Client", loglevel=level)

    # configure global websockets logging
    websocketslogger = logging.getLogger("websockets")
    configure_consoleNoTraceback_logger(websocketslogger, "Websock", logging.WARNING)

    clilogger.info("Starting MOTRA Client ...")


def client_defaultFileLogger(loglevel: str, logfile: str) -> None:

    clilogger = logging.getLogger("motra.cli")
    commonlogger = logging.getLogger("motra.common")
    clientlogger = logging.getLogger("motra.client")
    workspacelogger = logging.getLogger("motra.workspace")
    websocketslogger = logging.getLogger("websockets")

    file_handler = RotatingFileHandler(logfile, maxBytes=100 * 1024, backupCount=2)

    configure_contextfile_logger(
        clilogger,
        file_handler,
        logging.DEBUG,
    )

    configure_contextfile_logger(
        commonlogger,
        file_handler,
        logging.DEBUG,
    )

    configure_contextfile_logger(
        clientlogger,
        file_handler,
        logging.DEBUG,
    )

    configure_contextfile_logger(
        workspacelogger,
        file_handler,
        logging.DEBUG,
    )

    # configure_contextfile_logger(
    #     websocketslogger,
    #     file_handler,
    #     logging.DEBUG,
    # )
