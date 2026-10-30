#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import os
import logging
import csv
from io import StringIO
from utils import guest_ops
from pyVmomi import vim

logger = logging.getLogger(__name__)

prefix = "VCFOperationsvCommunity-"
suffix = "-OSInfo-TEMP"
current_directory = os.path.dirname(os.path.abspath(__file__))
osInfoScript = "getWindowsOSInformation.ps1"
osInfoScriptPath = os.path.join(current_directory, "getWindowsOSInformation.ps1")

OS_INFO_CSV = "OSInfo.csv"
COLUMNS = ("Name", "Version", "BuildNumber", "OSArchitecture", "LastBootUpTime", "ReleaseId")


def publish_os_information(vm_obj, vm_name: str, text: str) -> None:
    rows = list(csv.reader(StringIO(text)))
    if not rows:
        logger.info(f"Can not find Windows Operating System informations on {vm_name}")
        return
    header = rows[0]
    if any(column not in header for column in COLUMNS):
        logger.error(f"The Windows Operating System CSV on {vm_name} has no {', '.join(COLUMNS)} column.")
        return
    index = {column: header.index(column) for column in COLUMNS}

    for row in rows[1:]:
        try:
            os_values = {column: row[index[column]] for column in COLUMNS}
        except IndexError as e:
            logger.error(f"CSV parsing error on {vm_name}: {e}")
            continue

        logger.info(
            f"Parsed OS Information for {vm_name}: Name={os_values['Name']}, Version={os_values['Version']}, "
            f"BuildNumber={os_values['BuildNumber']}, Architecture={os_values['OSArchitecture']}, "
            f"LastBootUpTime={os_values['LastBootUpTime']}, ReleaseId={os_values['ReleaseId']}"
        )
        vm_obj.with_property("vCommunity|Guest OS|Operating System|OS Name", os_values["Name"])
        vm_obj.with_property("vCommunity|Guest OS|Operating System|OS Version", os_values["Version"])
        vm_obj.with_property("vCommunity|Guest OS|Operating System|OS BuildNumber", os_values["BuildNumber"])
        vm_obj.with_property("vCommunity|Guest OS|Operating System|OS Architecture", os_values["OSArchitecture"])
        vm_obj.with_property("vCommunity|Guest OS|Operating System|OS Last Boot Up Time", os_values["LastBootUpTime"])
        vm_obj.with_property("vCommunity|Guest OS|Operating System|OS Release ID", os_values["ReleaseId"])
        logger.info(f"Sending Windows Operating System informations for {vm_name}")


def collect_vm_os_information_properties(vm_obj, vm, content, winUser, winPassword):
    processManager = content.guestOperationsManager.processManager
    fileManager = content.guestOperationsManager.fileManager
    creds = vim.vm.guest.NamePasswordAuthentication(username=winUser, password=winPassword)

    toolsStatus = vm.guest.toolsStatus
    guestOSFamily = vm.guest.guestFamily
    if toolsStatus != "toolsOk" or guestOSFamily != "windowsGuest":
        logger.info(f"Skipping {vm.name} is not a Windows Guest.")
        return

    logger.info(f"Collecting Windows OS Information properties for {vm.name}")
    tempDir = None
    try:
        tempDir = fileManager.CreateTemporaryDirectory(vm, creds, prefix, suffix, guest_ops.TEMP_DIR_PATH)

        command = f"\"& '{tempDir}\\{osInfoScript}' | Export-Csv -Path '{tempDir}\\{OS_INFO_CSV}' -NoTypeInformation -Encoding UTF8\""
        if not guest_ops.transfer_file(vm, creds, content, osInfoScriptPath, tempDir, osInfoScript):
            logger.error(f"Cannot find the Windows Operating System information CSV file on {vm.name}")
            return

        guest_ops.run_powershell(processManager, vm, creds, command)
        OSInfoResult = guest_ops.read_guest_output(fileManager, vm, creds, f"{tempDir}\\{OS_INFO_CSV}")
        if OSInfoResult is None:
            logger.error(f"No Windows Operating System information was read from {vm.name}.")
            return
        publish_os_information(vm_obj, vm.name, OSInfoResult)

    except guest_ops.GuestProcessTimeout as e:
        logger.warning(f"Windows OS information skipped for {vm.name}: {e}")
    except Exception as e:
        logger.error(f"Windows OS information failed on {vm.name}: {e}")
    finally:
        guest_ops.remove_temp_dir(fileManager, vm, creds, tempDir)
