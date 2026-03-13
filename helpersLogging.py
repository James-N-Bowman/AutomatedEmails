import logging
import sys

# ---------------------------
# Hardcoded formats
# ---------------------------

VERBOSE_FMT = (
    "%(asctime)s | %(levelname)s | %(name)s | "
    "%(filename)s:%(lineno)d %(funcName)s() | %(message)s"
)

CONCISE_FMT = "%(levelname)s: %(message)s"


class SimpleLogger:
    """
    Wraps a logger and its single handler.
    """

    def __init__(
        self,
        name: str,
        level: str,
        verbose: bool = False,
        stream=sys.stdout,
        propagate: bool = False,
    ):
        self.logger = logging.getLogger(name)
        self.logger.propagate = propagate

        self.handler = logging.StreamHandler(stream)

        self.set_level(level)

        self.set_format(verbose)

        # Enforce single-handler rule
        self.logger.handlers.clear()
        self.logger.addHandler(self.handler)

    def set_level(self, level: str) -> None:
        """
        Set BOTH logger and handler to the same level.
        """
        level = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
            }.get(level.upper())
        self.logger.setLevel(level)
        self.handler.setLevel(level)

    def set_format(self, verbose: bool) -> None:
        """
        Switch between concise and verbose formats.
        """
        fmt = VERBOSE_FMT if verbose else CONCISE_FMT
        self.handler.setFormatter(logging.Formatter(fmt))