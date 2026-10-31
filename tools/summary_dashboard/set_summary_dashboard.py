"""Set or restore the Summary tab dashboard of one object type.

Replaces the built-in Summary page of an object type with a dashboard, the
same as Dashboards > Manage > (...) > Manage Summary Dashboards in the UI.
The UI call is undocumented (no Suite API exists for it); see ui_client.py.

The server copies the dashboard into a Summary template; editing the source
dashboard later does not change the Summary tab. Run this again to publish
an update.

Usage:
    python set_summary_dashboard.py <adapter_kind> <resource_kind> "<dashboard name>" <dashboard uuid>
    python set_summary_dashboard.py <adapter_kind> <resource_kind> --restore

Examples:
    python set_summary_dashboard.py VMWARE Folder ". Object Summary Page for Folder" d22b04d0-1eb2-496e-8944-a143e94187d5
    python set_summary_dashboard.py VMWARE Folder --restore

Connection: set VCFOPS_HOST, VCFOPS_USER and VCFOPS_PW in the environment.

Acknowledgment: the UI session client (ui_client.py) is adapted from the
vcf-content-factory project by Scott Bowe, https://github.com/sentania-labs/vcf-content-factory
(profile: https://www.linkedin.com/in/scottrbowe/). See the header of ui_client.py.
"""
from __future__ import annotations

import os
import sys

from ui_client import UIClientError, VCFOpsUIClient


def resource_kind_id(adapter_kind: str, resource_kind: str) -> str:
    """The id the UI uses for a kind: "0020" + two-digit length of the adapter kind + both names.

    Example: VMWARE Folder -> "002006VMWAREFolder".
    """
    return f"0020{len(adapter_kind):02d}{adapter_kind}{resource_kind}"


def _find_kind(ui: VCFOpsUIClient, adapter_kind: str, resource_kind: str) -> dict:
    listing = ui.get_resource_kind_list(adapter_kind)
    for entry in listing.get("resourceKindList", []):
        if entry.get("resourceKind") == resource_kind:
            return {"entry": entry, "default": listing["defaultTemplateName"]}
    raise UIClientError(f"resource kind {adapter_kind}:{resource_kind} not found on the instance")


def set_summary_dashboard(
    ui: VCFOpsUIClient,
    adapter_kind: str,
    resource_kind: str,
    dashboard_name: str,
    dashboard_uuid: str,
) -> dict:
    """Bind ``dashboard_name``/``dashboard_uuid`` to the Summary tab of the kind.

    Returns the ``getSummaryTabId`` answer read back after the write, so the
    caller can check ``isDashboard`` and ``tabId``.
    """
    rk_id = resource_kind_id(adapter_kind, resource_kind)
    key = f"resourceKind_{rk_id}"
    ui.associate_resource_kind_dashboards({key: f"{dashboard_name}_::_{dashboard_uuid}"})
    return ui.get_summary_tab_id(rk_id)


def restore_summary_page(ui: VCFOpsUIClient, adapter_kind: str, resource_kind: str) -> dict:
    """Restore the built-in Summary page ("Use Default") of the kind."""
    rk_id = resource_kind_id(adapter_kind, resource_kind)
    info = _find_kind(ui, adapter_kind, resource_kind)
    # A kind with a built-in summary page carries its own defaultTemplateName; otherwise the global one.
    default = info["entry"].get("defaultTemplateName", info["default"])
    ui.associate_resource_kind_dashboards({}, {f"resourceKind_{rk_id}": default})
    return ui.get_summary_tab_id(rk_id)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    adapter_kind, resource_kind = argv[0], argv[1]
    host = os.environ["VCFOPS_HOST"]
    user = os.environ["VCFOPS_USER"]
    password = os.environ["VCFOPS_PW"]
    with VCFOpsUIClient(host, user, password, verify_ssl=False) as ui:
        if argv[2] == "--restore":
            answer = restore_summary_page(ui, adapter_kind, resource_kind)
        else:
            if len(argv) != 4:
                print(__doc__)
                return 2
            answer = set_summary_dashboard(ui, adapter_kind, resource_kind, argv[2], argv[3])
    print(f"{adapter_kind}:{resource_kind} summary tab now: {answer}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
