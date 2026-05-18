# QAOA category: operations, domain: technology
"""OS desktop automation tools (Computer Use style, opt-in)."""

from .desktop_tools import create_desktop_tools
from .desktop_utils import check_desktop_requirements, check_desktop_requirements_detail

__all__ = [
    "check_desktop_requirements",
    "check_desktop_requirements_detail",
    "create_desktop_tools",
]
