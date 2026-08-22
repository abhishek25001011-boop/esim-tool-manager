"""Logging configuration shared by application modules."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a logger, configuring a concise console handler once."""
    root = logging.getLogger("esim_tool_manager")
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)
        root.setLevel(logging.INFO)
    return root.getChild(name)
