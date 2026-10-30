#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

import os
import time
import logging
import csv
from io import StringIO
from typing import List, Optional
from utils import guest_ops
from pyVmomi import vim
from aria.ops.event import Criticality

logger = logging.getLogger(__name__)

prefix = "VCFOperationsvCommunity-"
suffix = "-EventLog-TEMP"
current_directory = os.path.dirname(os.path.abspath(__file__))
eventLogScript = "getWindowsEventLogs.ps1"
eventLogScriptPath = os.path.join(current_directory, "getWindowsEventLogs.ps1")

EVENT_LOG_CSV = "Event_Log.csv"
# One VM sends at most this many events in a cycle. The script returns one event per log and event ID, so this only
# limits a long event list in the configuration file. The rest is counted in the log.
MAX_EVENTS_PER_VM = 100

_CRITICALITY = {
    "Information": Criticality.INFO,
    "Verbose": Criticality.INFO,
    "Warning": Criticality.WARNING,
    "Error": Criticality.IMMEDIATE,
    "Critical": Criticality.CRITICAL,
}


def criticality_for(level: str) -> Criticality:
    return _CRITICALITY.get(level, Criticality.INFO)


def format_event_message(level: str, message: str) -> str:
    return f"[WindowsEvent-{level} {message}]"


def parse_event_rows(text: str) -> List[List[str]]:
    """The data rows of the event CSV, with the header removed. Empty when there is no text."""
    if not text.strip():
        return []
    return list(csv.reader(StringIO(text)))[1:]


def event_columns(text: str) -> Optional[tuple]:
    """The column positions of Level and Event in the CSV header, or None when either is missing."""
    rows = list(csv.reader(StringIO(text)))
    if not rows:
        return None
    header = rows[0]
    if "Level" not in header or "Event" not in header:
        return None
    return header.index("Level"), header.index("Event")


def publish_events(vm_obj, vm_name: str, text: str) -> None:
    columns = event_columns(text)
    if columns is None:
        logger.error(f"The Windows Event CSV on {vm_name} has no Level or Event column.")
        return
    level_index, message_index = columns
    rows = parse_event_rows(text)
    if not rows:
        logger.info(f"Can not find Windows Event details on {vm_name}")
        return

    now = int(time.time() * 1000)
    sent = 0
    for row in rows:
        if sent >= MAX_EVENTS_PER_VM:
            break
        try:
            event_level = row[level_index]
            event_message = row[message_index]
        except IndexError as e:
            logger.error(f"CSV parsing error on {vm_name}: {e}")
            continue

        vm_obj.with_event(
            message=format_event_message(event_level, event_message),
            criticality=criticality_for(event_level),
            auto_cancel=True,
            watch_wait_cycle=1,
            cancel_wait_cycle=3,
            update_date=now
        )
        sent += 1
        logger.info(f"Sending Windows Event details for {vm_name}")

    if len(rows) > MAX_EVENTS_PER_VM:
        logger.warning(
            f"{vm_name} has {len(rows)} Windows events. Only the first {MAX_EVENTS_PER_VM} are sent this cycle."
        )


def collect_windows_events(vm_obj, vm, content, winUser, winPassword, winEventLogConfigFile):
    processManager = content.guestOperationsManager.processManager
    fileManager = content.guestOperationsManager.fileManager
    creds = vim.vm.guest.NamePasswordAuthentication(username=winUser, password=winPassword)

    toolsStatus = vm.guest.toolsStatus
    guestOSFamily = vm.guest.guestFamily
    if toolsStatus != "toolsOk" or guestOSFamily != "windowsGuest":
        logger.info(f"Skipping {vm.name} is not a Windows Guest.")
        return

    logger.info(f"Started Windows Event log reading for {vm.name}")
    tempDir = None
    try:
        tempDir = fileManager.CreateTemporaryDirectory(vm, creds, prefix, suffix, guest_ops.TEMP_DIR_PATH)
        tempFileStatus, tempFile = guest_ops.create_temp_file(fileManager, vm, creds, tempDir, winEventLogConfigFile)
        if not tempFileStatus:
            logger.error(f"Cannot write the Windows Event Log XML file on {vm.name}")
            return

        tempFileName = tempFile.split("EventLog-TEMP\\")[-1]
        if not guest_ops.file_exists(fileManager, vm, creds, tempDir, tempFileName):
            logger.error(f"Cannot find the Windows Event Log XML file on {vm.name}")
            return

        command = f"\"& '{tempDir}\\{eventLogScript}' '{tempFile}' | Export-Csv -Path '{tempDir}\\{EVENT_LOG_CSV}' -NoTypeInformation -Encoding UTF8\""
        if not guest_ops.transfer_file(vm, creds, content, eventLogScriptPath, tempDir, eventLogScript):
            logger.info(f"File transfer failed. Skipping Windows Event Log reading on {vm.name} ")
            return

        guest_ops.run_powershell(processManager, vm, creds, command)
        eventLogResult = guest_ops.read_guest_output(fileManager, vm, creds, f"{tempDir}\\{EVENT_LOG_CSV}")
        if eventLogResult is None:
            logger.error(f"No Windows Event details were read from {vm.name}.")
            return
        publish_events(vm_obj, vm.name, eventLogResult)

    except guest_ops.GuestProcessTimeout as e:
        logger.warning(f"Windows Event Log reading skipped for {vm.name}: {e}")
    except Exception as e:
        logger.error(f"An error occurred during Windows Event Log collection on {vm.name}: {e}")
    finally:
        guest_ops.remove_temp_dir(fileManager, vm, creds, tempDir)
