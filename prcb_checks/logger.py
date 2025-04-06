"""logger.py: Logger module for prcb-checks."""

import logging
import sys

# Set Logger
logger = logging.getLogger("prcb_checks")

# Set Handler
console_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Set default log legel
logger.setLevel(logging.INFO)


def set_debug_mode(enabled=False):
    """
    Set debug mode

    Args:
        enabled (bool): Whether to enable debug mode
    """
    if enabled:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    else:
        logger.setLevel(logging.INFO)
