import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


# we add a file based logger to the default handler
# this will cause fastAPI to generate data inside a file in addition to the default
# console handler
def configure_file_logger(
    logger: logging.Logger, log_file_path: Path = Path("measurement.log")
) -> logging.Logger:
    """
    Configures a default file logger. This should show most of the relevant data
    as well as existing Traces from recent exceptions
    """
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=100 * 1024, backupCount=2
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def configure_contextfile_logger(
    logger: logging.Logger,
    file_handler: logging.FileHandler,
    loglevel=logging.DEBUG,
    enable_context: bool = True,
) -> logging.Logger:
    """
    Configures a logger to emit data frames, if present in the stream.

    loggers of the form:\n
    f"Client: Parsed REQUEST_UPLOAD header",extra={"data": request.model_dump()},\n
    will be dumped in the filehandler

    Parameters:
        enable_context(Bool): controls if extra data is written to a file
        file_handler: logging filehandler, so we can append from multiple loggers into a single file

    """

    if enable_context:
        formatter = ContextFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(data)s"
        )
    else:
        formatter = ContextFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    file_handler.setLevel(loglevel)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def configure_consoleNoTraceback_logger(
    logger: logging.Logger,
    role: str,
    loglevel=logging.INFO,
) -> logging.Logger:
    """
    Configures a default console logger, to supress exception traces.
    Should be used with the context/file loggers to keep the execution logs
    clean.
    """

    GREEN = "\x1b[32m"
    RESET = "\x1b[0m"
    format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    )

    formatter = logging.Formatter(
        # "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        # fmt=f"{GREEN}%(levelname)-8s{RESET} {role} - %(message)-80s -  %(funcName)s:%(lineno)d:%(filename)s",
        fmt=f"{GREEN}%(levelname)-8s{RESET} {role} - %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler = logging.StreamHandler(sys.stdout)

    console_handler.setFormatter(formatter)
    console_handler.addFilter(NoTracebackFilter())
    console_handler.setLevel(loglevel)
    logger.addHandler(console_handler)

    return logger


class NoTracebackFilter(logging.Filter):
    """
    A custom filter to prevent multi-line traceback messages from being
    emitted by a specific handler.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        This method is called for every log record.

        It checks if the record has exception info. If it does, it suppresses
        the traceback for this handler by clearing the exc_info and exc_text
        attributes of the record.
        """
        if record.exc_info:
            # If there's an exception, we'll still log the message,
            # but we clear the traceback details for this specific handler.
            record.exc_info = None
            record.exc_text = ""

        # Always return True to allow the (now modified) record to be processed.
        return True


class ContextFormatter(logging.Formatter):
    """
    A custom formatter that allows for default values for extra parameters.
    """

    def format(self, record):
        # Set default values for your custom keys if they don't exist
        record.data = getattr(record, "data", "N/A")
        log_string = super().format(record)
        if record.exc_info:
            log_string += "\n" + self.formatException(record.exc_info)
        return log_string


# def get_motra_server_logger(name: str) -> logging.Logger:
#     """
#     Returns a logger for a motra (server) module, ensuring it's a child of the
#     configured Uvicorn-Motra hierarchy.
#     """
#     # If name is 'motra.server.processor', this becomes 'uvicorn.error.motra.server.processor'
#     # This assumes your internal modules use __name__ like 'motra.server.processor'
#     if name.startswith("motra."):
#         return logging.getLogger(f"uvicorn.error.{name}")
#     else:
#         # Fallback for modules not strictly within motra, or if __name__ is __main__
#         return logging.getLogger(f"uvicorn.error.motra.{name}")
