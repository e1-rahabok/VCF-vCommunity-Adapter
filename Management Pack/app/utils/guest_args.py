#  Copyright 2026 VCF Operations vCommunity Management Pack
"""Values from the configuration files that end up in a PowerShell command run inside a Windows guest.

The Windows Service names come from windows_service_list.xml, which a VCF Operations user with access to the
configuration files can edit. A name is put between single quotes in the command line, so a name with a quote in it
would end the quoted text and run what follows in every monitored VM, under the Windows credential of the adapter.
Only names that cannot do that are accepted. The rest are left out and logged once.
"""
import logging
import re
from typing import Iterable, List, Tuple

logger = logging.getLogger(__name__)

# What a Windows service short name uses in practice, such as Dhcp, WinDefend, MSSQL$SQLEXPRESS, vmicheartbeat.
# No quotes of any kind (the curly ones too: PowerShell reads them as quotes), no backtick, no $( ), no ; | & < >,
# no wildcards (Get-Service -Name takes them), no new line.
_SERVICE_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9 _.$#@()+\-]{0,255}$")


def is_safe_service_name(name) -> bool:
    return isinstance(name, str) and _SERVICE_NAME.fullmatch(name) is not None and "$(" not in name


def split_service_names(names: Iterable) -> Tuple[List[str], List]:
    """(safe names, rejected names), in the order given."""
    safe, rejected = [], []
    for name in names or []:
        (safe if is_safe_service_name(name) else rejected).append(name)
    return safe, rejected


def safe_service_names(names: Iterable) -> List[str]:
    """The names that are safe to use. Logs the others once, and leaves them out."""
    safe, rejected = split_service_names(names)
    if rejected:
        logger.warning(
            f"Windows Service names left out because they contain characters that are not allowed "
            f"(letters, digits, space and _ . $ # @ ( ) + - only): {[repr(name)[:80] for name in rejected]}. "
            f"Fix the entries in the Windows Service configuration file."
        )
    return safe


def powershell_string_array(names: Iterable) -> str:
    """@('a', 'b'): the names as a PowerShell array of single-quoted strings.

    Raises ValueError when a name is not safe, so a caller that forgot to check cannot build an unsafe command.
    """
    names = list(names or [])
    _, rejected = split_service_names(names)
    if rejected:
        raise ValueError(f"Not a safe Windows Service name: {repr(rejected[0])[:80]}")
    return "@(" + ", ".join(f"'{name}'" for name in names) + ")"
