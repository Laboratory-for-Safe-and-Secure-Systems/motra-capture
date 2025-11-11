import logging
from logging.handlers import RotatingFileHandler

from motra.logging.log_config import (
    configure_consoleNoTraceback_logger,
    configure_contextfile_logger,
)


def server_defaultConsoleLogger(loglevel: str) -> None:
    # setup the provided global log level
    level = getattr(logging, loglevel.upper())

    # remove the default global loghandler
    logging.basicConfig(level=level, datefmt="%H:%M:%S")
    logging.getLogger("").removeHandler(logging.getLogger("").handlers[0])

    # setup custom handlers downstream
    log = logging.getLogger("motra.cli")
    log = configure_consoleNoTraceback_logger(log, "CLI", level)

    commonlogger = logging.getLogger("motra.common")
    configure_consoleNoTraceback_logger(commonlogger, "Server-Common", level)

    workspacelogger = logging.getLogger("motra.workspace")
    configure_consoleNoTraceback_logger(workspacelogger, "Server-WS", level)

    serverlogger = logging.getLogger("motra.server")
    configure_consoleNoTraceback_logger(serverlogger, "Server", level)

    serverlogger = logging.getLogger("sh")
    configure_consoleNoTraceback_logger(serverlogger, "pySH", level)

    log.info("Starting MOTRA Server ...")


def server_defaultFileLogger(loglevel: str, logfile: str) -> None:

    level = getattr(logging, loglevel.upper())
    file_handler = RotatingFileHandler(logfile, maxBytes=100 * 1024, backupCount=2)

    serverlogger = logging.getLogger("motra.server")
    configure_contextfile_logger(
        logger=serverlogger,
        file_handler=file_handler,
        loglevel=level,
    )

    commonlogger = logging.getLogger("motra.common")
    configure_contextfile_logger(
        logger=commonlogger,
        file_handler=file_handler,
        loglevel=level,
    )

    clilogger = logging.getLogger("motra.cli")
    configure_contextfile_logger(
        logger=clilogger,
        file_handler=file_handler,
        loglevel=level,
    )

    workspacelogger = logging.getLogger("motra.workspace")
    configure_contextfile_logger(
        logger=workspacelogger,
        file_handler=file_handler,
        loglevel=level,
    )
