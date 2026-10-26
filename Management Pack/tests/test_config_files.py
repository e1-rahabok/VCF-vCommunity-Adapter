#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Configuration files of an Adapter Instance: the list they hold, and the problems that are reported.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from utils import config_files as cf


def test_the_text_is_a_comma_separated_list():
    text = "<vmConfigs>\n  <!-- a comment is not text -->\n  disk.EnableUUID, tools.syncTime ,\n</vmConfigs>"
    assert cf.parse_list(text) == ["disk.EnableUUID", "tools.syncTime"]


def test_empty_text_gives_an_empty_list():
    assert cf.parse_list("") == []
    assert cf.parse_list("   ") == []
    assert cf.parse_list("<vmConfigs/>") == []


def test_invalid_xml_is_refused():
    try:
        cf.parse_list("<vmConfigs>a, b")
    except ET.ParseError:
        return
    raise AssertionError("invalid XML was accepted")


def test_check_xml_gives_the_reason_or_none():
    assert cf.check_xml("<Events><Event/></Events>") is None
    assert cf.check_xml("<Events>") is not None


def test_problem_texts_name_the_file_and_say_what_is_lost():
    missing = cf.missing_problem("vm_options", 404)
    assert "'vm_options.xml'" in missing and "HTTP 404" in missing and "Nothing is collected" in missing
    invalid = cf.invalid_problem("vm_options", "mismatched tag")
    assert "'vm_options.xml'" in invalid and "mismatched tag" in invalid and "Nothing is collected" in invalid
