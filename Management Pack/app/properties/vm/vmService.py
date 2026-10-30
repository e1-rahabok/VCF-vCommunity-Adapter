#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import csv
import os
import logging
from io import StringIO
from typing import List, NamedTuple, Optional

from utils import guest_args
from utils import guest_ops
from pyVmomi import vim

logger = logging.getLogger(__name__)

prefix = "VCFOperationsvCommunity-"
suffix = "-Services-TEMP"
current_directory = os.path.dirname(os.path.abspath(__file__))
serviceLogScript = "getWindowsServices.ps1"
serviceScriptPath = os.path.join(current_directory, "getWindowsServices.ps1")

SERVICES_CSV = "Services.csv"
COLUMNS = ("Name", "DisplayName", "Status", "StartType")


class ServiceRow(NamedTuple):
    name: str
    display_name: str
    status: str
    start_type: str


def parse_services(text: str) -> Optional[List[ServiceRow]]:
    """The services of the CSV that the PowerShell script writes. None when a column is missing.

    The CSV is parsed with the csv module, so a display name with a comma in it stays in one field.
    """
    if not text.strip():
        return []
    rows = list(csv.reader(StringIO(text)))
    header = rows[0]
    if any(column not in header for column in COLUMNS):
        return None
    index = {column: header.index(column) for column in COLUMNS}
    services = []
    for row in rows[1:]:
        if len(row) < len(header):
            logger.warning(f"Skipping a Windows Service row with {len(row)} fields, expected {len(header)}.")
            continue
        services.append(ServiceRow(*(row[index[column]] for column in COLUMNS)))
    return services


def publish_services(vm_obj, vm_name: str, text: str) -> None:
    services = parse_services(text)
    if services is None:
        logger.error(f"The Windows Service CSV on {vm_name} has no {', '.join(COLUMNS)} column.")
        return
    if not services:
        logger.info(f"Can not find Windows Service details on {vm_name}")
        return
    for service in services:
        vm_obj.with_property(f"vCommunity|Guest OS|Services:{service.display_name}|Service Name", service.name)
        vm_obj.with_property(f"vCommunity|Guest OS|Services:{service.display_name}|Service Status", service.status)
        vm_obj.with_property(f"vCommunity|Guest OS|Services:{service.display_name}|Service Start Type", service.start_type)
        logger.info(f"Sending Windows Service details for {vm_name}")


def collect_vm_service_properties(vm_obj, vm, content, winUser, winPassword, winServiceConfigFile):
    processManager = content.guestOperationsManager.processManager
    fileManager = content.guestOperationsManager.fileManager
    creds = vim.vm.guest.NamePasswordAuthentication(username=winUser, password=winPassword)

    toolsStatus = vm.guest.toolsStatus
    guestOSFamily = vm.guest.guestFamily
    if toolsStatus != "toolsOk" or guestOSFamily != "windowsGuest":
        logger.info(f"Skipping {vm.name} is not a Windows Guest.")
        return

    logger.info(f"Started Windows Service monitoring for {vm.name}")
    tempDir = None
    try:
        tempDir = fileManager.CreateTemporaryDirectory(vm, creds, prefix, suffix, guest_ops.TEMP_DIR_PATH)

        serviceList = guest_args.powershell_string_array(winServiceConfigFile)
        command = f"\"& '{tempDir}\\{serviceLogScript}' @({serviceList}) | Export-Csv -Path '{tempDir}\\{SERVICES_CSV}' -NoTypeInformation -Encoding UTF8\""
        if not guest_ops.transfer_file(vm, creds, content, serviceScriptPath, tempDir, serviceLogScript):
            logger.error(f"Cannot find the Windows Service CSV file on {vm.name}")
            return

        guest_ops.run_powershell(processManager, vm, creds, command)
        serviceResult = guest_ops.read_guest_output(fileManager, vm, creds, f"{tempDir}\\{SERVICES_CSV}")
        if serviceResult is None:
            logger.error(f"No Windows Service details were read from {vm.name}.")
            return
        publish_services(vm_obj, vm.name, serviceResult)

    except guest_ops.GuestProcessTimeout as e:
        logger.warning(f"Windows Service monitoring skipped for {vm.name}: {e}")
    except Exception as e:
        logger.error(f"Windows Service monitoring failed on {vm.name}: {e}")
    finally:
        guest_ops.remove_temp_dir(fileManager, vm, creds, tempDir)
