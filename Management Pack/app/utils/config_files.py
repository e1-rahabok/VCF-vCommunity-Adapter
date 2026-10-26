#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Reads the configuration files of an Adapter Instance: the lists of settings that the pack collects.

A file is an XML document whose text is a comma-separated list, such as the names of the settings to collect.
A file that is missing, or is not valid XML, gives an empty list for that file only. The problem is also
reported to the user, as an event on the vCenter object (see collectors/vcenter/collectvCenterData.py). The rest of
the collection goes on, so one bad file does not stop the others.

Docs: docs/troubleshooting-guide/configuration-files.md
"""
import xml.etree.ElementTree as ET
from typing import List, Optional


def parse_list(text: Optional[str]) -> List[str]:
    """The items of a configuration file: its text, split on commas. Empty text gives []. Raises ParseError when
    the text is not valid XML."""
    if not (text or "").strip():
        return []
    root = ET.fromstring(text)
    return [item.strip() for item in (root.text or "").split(",") if item.strip()]


def check_xml(text: Optional[str]) -> Optional[str]:
    """None when the text is valid XML, else the parser's reason. For a file that is passed on as it is."""
    try:
        ET.fromstring(text or "")
        return None
    except ET.ParseError as e:
        return str(e)


def missing_problem(file_name: str, status_code: int) -> str:
    """The problem text for a file that VCF Operations could not return."""
    return (f"Configuration file '{file_name}.xml' could not be read from VCF Operations (HTTP {status_code}). "
            f"Nothing is collected from it. Check the file name set on the Adapter Instance.")


def invalid_problem(file_name: str, reason: str) -> str:
    """The problem text for a file that is not valid XML."""
    return (f"Configuration file '{file_name}.xml' is not valid XML ({reason}). Nothing is collected from it "
            f"until it is corrected.")
