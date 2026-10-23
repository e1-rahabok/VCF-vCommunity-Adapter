#  Copyright 2026 VCF Operations vCommunity Management Pack
"""The bulk importer sets the TLS settings of each Adapter Instance, and refuses a row that contradicts itself.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import importlib.util
from pathlib import Path

import pytest

IMPORTER = Path(__file__).resolve().parents[2] / "tools" / "importer" / "importer.py"
SHA256 = ":".join(["AB"] * 32)

spec = importlib.util.spec_from_file_location("importer", IMPORTER)
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)

HEADER = "vcenter_host,vcenter_user,vcenter_password,vcenter_tls_validation,vcenter_thumbprint,guest_tls_validation"


def rows(tmp_path, *lines):
    path = tmp_path / "vcenters.csv"
    path.write_text("\n".join([HEADER, *lines]) + "\n", encoding="utf-8")
    return importer.read_csv(str(path))


def identifiers(row):
    return {i["name"]: i["value"] for i in importer.build_resource_identifiers(row)}


def test_a_row_with_no_tls_columns_gets_the_defaults(tmp_path):
    path = tmp_path / "vcenters.csv"
    path.write_text("vcenter_host,vcenter_user,vcenter_password\nvc01,svc,pw\n", encoding="utf-8")
    ids = identifiers(importer.read_csv(str(path))[0])
    assert ids["vcenter_tls_validation"] == "Trust on First Use"
    assert ids["guest_tls_validation"] == "Pinned"
    assert "vcenter_thumbprint" not in ids


def test_a_pinned_row_carries_its_thumbprint(tmp_path):
    ids = identifiers(rows(tmp_path, f"vc01,svc,pw,Pinned,{SHA256},")[0])
    assert ids["vcenter_tls_validation"] == "Pinned"
    assert ids["vcenter_thumbprint"] == SHA256
    assert ids["guest_tls_validation"] == "Pinned"


def test_the_mode_is_written_in_its_canonical_spelling(tmp_path):
    ids = identifiers(rows(tmp_path, "vc01,svc,pw,trust on first use,,strict")[0])
    assert ids["vcenter_tls_validation"] == "Trust on First Use" and ids["guest_tls_validation"] == "Strict"


def test_pinned_without_a_thumbprint_is_refused(tmp_path):
    with pytest.raises(ValueError, match="Pinned, but vcenter_thumbprint is empty"):
        rows(tmp_path, "vc01,svc,pw,Pinned,,")


def test_a_thumbprint_without_pinned_is_refused(tmp_path):
    with pytest.raises(ValueError, match="Set it to Pinned"):
        rows(tmp_path, f"vc01,svc,pw,Enabled,{SHA256},")


@pytest.mark.parametrize("thumbprint", ["AB" * 20, "zz" * 32, "AB" * 31])
def test_a_bad_thumbprint_is_refused(tmp_path, thumbprint):
    with pytest.raises(ValueError, match="SHA-256"):
        rows(tmp_path, f"vc01,svc,pw,Pinned,{thumbprint},")


def test_an_unknown_mode_is_refused_not_treated_as_off(tmp_path):
    with pytest.raises(ValueError, match="vcenter_tls_validation must be one of"):
        rows(tmp_path, "vc01,svc,pw,Off,,")
    with pytest.raises(ValueError, match="guest_tls_validation must be one of"):
        rows(tmp_path, "vc01,svc,pw,Enabled,,Enabled")


def test_the_importer_and_the_adapter_agree_on_the_names_and_values():
    """The importer repeats the identifier names of the adapter: a rename in one must show here."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
    from constants import main as constants
    from utils import guest_http, tls
    assert importer.IDENTIFIER_VCENTER_TLS_VALIDATION == constants.VCENTER_TLS_VALIDATION
    assert importer.IDENTIFIER_VCENTER_THUMBPRINT == constants.VCENTER_THUMBPRINT
    assert importer.IDENTIFIER_GUEST_TLS_VALIDATION == constants.GUEST_TLS_VALIDATION
    assert importer.VCENTER_TLS_MODES == tuple(tls.VCENTER_MODES)
    assert importer.GUEST_TLS_MODES == tuple(guest_http.GUEST_MODES)
    assert importer.DEFAULTS["vcenter_tls_validation"] == tls.DEFAULT_VCENTER_MODE
    assert importer.DEFAULTS["guest_tls_validation"] == guest_http.DEFAULT_GUEST_MODE
