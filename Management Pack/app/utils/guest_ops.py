#  Copyright 2026 VCF Operations vCommunity Management Pack
"""The GuestAPI steps that the Windows guest collectors share: services, OS information and event logs.

For a VMware administrator
--------------------------
Each collector copies a small PowerShell script into a temporary folder inside the Windows VM, runs it, and reads back
the CSV file it writes. VMware Tools carries every step. Nothing runs unless the VM is powered on, has Tools running
and is a Windows guest, and the credentials of the Adapter Instance are used for each step.

A step that does not finish is stopped after PROCESS_TIMEOUT_SECONDS, and the VM is skipped for that cycle with a
warning in the adapter log. The whole cycle has a time budget for guest work too: see GuestBudget.
"""
import logging
import time
from typing import Any, Callable, Optional, Tuple

from pyVmomi import vim
from utils import guest_http

logger = logging.getLogger(__name__)

SYSTEM_ROOT = "C:\\Windows"
TEMP_DIR_PATH = SYSTEM_ROOT + "\\Temp"
POWERSHELL_PATH = SYSTEM_ROOT + "\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"

# A PowerShell step that has not exited after this long is stopped. Each script reads a few hundred objects, so
# five minutes is far above a normal run.
PROCESS_TIMEOUT_SECONDS = 300
# The poll interval doubles from one second up to this value, so a short step is seen quickly and a long one is not
# polled every second.
POLL_MAX_SECONDS = 10
# Guest work of one collection cycle, across all VMs. When it is spent, the remaining VMs are skipped for the cycle,
# so a slow estate cannot make one cycle run for hours.
GUEST_BUDGET_SECONDS = 1800


class GuestProcessTimeout(RuntimeError):
    """A PowerShell step in the guest did not finish in time. It was stopped, and the VM is skipped for this cycle."""


class GuestBudget:
    """The time left for guest monitoring in one collection cycle. Created at the start of the VM collection, and
    asked by has_time() before the guest steps of each VM. Once the budget is spent, the remaining VMs are skipped."""

    def __init__(self, seconds: float = GUEST_BUDGET_SECONDS, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._deadline = clock() + seconds
        self.skipped = 0
        self._warned = False

    def has_time(self) -> bool:
        if self._clock() < self._deadline:
            return True
        self.skipped += 1
        if not self._warned:
            self._warned = True
            logger.warning(
                f"The guest time budget of {GUEST_BUDGET_SECONDS // 60} minutes for this collection is spent. "
                "Windows guest monitoring is skipped for the remaining VMs until the next cycle."
            )
        return False


def transfer_file(vm: Any, creds: Any, content: Any, script_path: str, temp_dir: str, script_name: str) -> bool:
    """Copies a local script into temp_dir in the guest. True when the host accepted it."""
    try:
        with open(script_path, "rb") as f:
            data = f.read()

        remote_path = f"{temp_dir}\\{script_name}"
        file_manager = content.guestOperationsManager.fileManager
        file_attributes = vim.vm.guest.FileManager.FileAttributes()

        url = file_manager.InitiateFileTransferToGuest(
            vm=vm,
            auth=creds,
            guestFilePath=remote_path,
            fileAttributes=file_attributes,
            fileSize=len(data),
            overwrite=True
        )

        response = guest_http.put(vm, url, data)
        if response.status_code == 200:
            logger.info(f"Successfully transferred the {remote_path} file to {vm.name}")
            return True
        logger.error(f"File transfer failed to {vm.name}: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        logger.exception(f"Exception during file transfer to {vm.name}: {e}")
        return False


def run_powershell(
    process_manager: Any,
    vm: Any,
    creds: Any,
    command: str,
    timeout: float = PROCESS_TIMEOUT_SECONDS,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> Optional[int]:
    """Runs a PowerShell command in the guest and waits for it. Returns its exit code.

    Raises GuestProcessTimeout when the command is still running after timeout seconds. The process is stopped first.
    """
    program_spec = vim.vm.guest.ProcessManager.ProgramSpec(
        programPath=POWERSHELL_PATH,
        arguments=f"-Command \"{command}\""
    )
    pid = process_manager.StartProgram(vm, creds, program_spec)
    if pid <= 0:
        raise RuntimeError(f"Command execution failed on {vm.name}")
    logger.info(f"Powershell command has been executed by command: {command} , PID: {pid}")

    deadline = clock() + timeout
    delay = 1.0
    while True:
        processes = process_manager.ListProcessesInGuest(vm, creds, [pid])
        if not processes:
            # The guest no longer lists the process, so it has finished. Its exit code is not known.
            logger.warning(f"Process {pid} on {vm.name} is no longer listed, and its exit code is unknown.")
            return None
        exit_code = processes[0].exitCode
        if exit_code is not None:
            logger.info(f"Code execution finished, exit code: {exit_code}")
            return exit_code
        if clock() >= deadline:
            _stop_process(process_manager, vm, creds, pid)
            raise GuestProcessTimeout(
                f"The PowerShell step on {vm.name} did not finish in {int(timeout)} seconds, so it was stopped."
            )
        sleep(delay)
        delay = min(delay * 2, POLL_MAX_SECONDS)


def _stop_process(process_manager: Any, vm: Any, creds: Any, pid: int) -> None:
    try:
        process_manager.TerminateProcess(vm, creds, pid)
    except Exception as e:
        logger.warning(f"Could not stop process {pid} on {vm.name}: {e}")


def file_exists(file_manager: Any, vm: Any, creds: Any, temp_dir: str, file_name: str) -> bool:
    try:
        file_info = file_manager.ListFilesInGuest(
            vm=vm,
            auth=creds,
            filePath=temp_dir,
            index=0,
            maxResults=100
        )

        if file_info.files:
            for file in file_info.files:
                if file.path.lower() == file_name.lower():
                    logger.info(f"{file_name} file found in {temp_dir} on {vm.name}")
                    return True
        return False
    except vim.fault.FileNotFound:
        logger.info(f"Couldn't find the {file_name} in {vm.name}")
        return False
    except Exception as e:
        logger.error(f"There was an error during file check. {e}")
        return False


def read_guest_output(file_manager: Any, vm: Any, creds: Any, file_path: str) -> Optional[str]:
    """The text of a file in the guest. None when the download fails: the caller must not read it as empty."""
    read_file = file_manager.InitiateFileTransferFromGuest(vm, creds, file_path)
    response = guest_http.get(vm, read_file.url)
    if response.status_code == 200:
        logger.info(f"Successfuly downloaded the file: {file_path} from {vm.name}")
        return response.text
    logger.error(f"Can not download powershell output from {vm.name}. Expected file is: {file_path}")
    return None


def create_temp_file(file_manager: Any, vm: Any, creds: Any, directory: str, data: str) -> Tuple[bool, Optional[str]]:
    """Creates a temporary XML file in the guest and writes data into it. (True, its path), or (False, None)."""
    try:
        temp_file = file_manager.CreateTemporaryFileInGuest(vm, creds, prefix="events", suffix=".xml", directoryPath=directory)
        file_attributes = vim.vm.guest.FileManager.FileAttributes()
        url = file_manager.InitiateFileTransferToGuest(
            vm=vm,
            auth=creds,
            guestFilePath=temp_file,
            fileAttributes=file_attributes,
            fileSize=len(data),
            overwrite=True
        )

        response = guest_http.put(vm, url, data)
        if response.status_code == 200:
            logger.info(f"XML data successfully written to {temp_file} on {vm.name}")
            return True, temp_file
        logger.error(f"Failed to write file. HTTP status: {response.status_code} on {vm.name}")
        return False, None
    except Exception as e:
        logger.error(f"Exception during file creation on {vm.name}: {e}")
        return False, None


def remove_temp_dir(file_manager: Any, vm: Any, creds: Any, temp_dir: Optional[str]) -> None:
    """Deletes the temporary folder of one collection in the guest. Never raises: it runs in a finally block."""
    if not temp_dir:
        return
    try:
        file_manager.DeleteDirectoryInGuest(vm, creds, temp_dir, True)
    except Exception as e:
        logger.warning(f"Could not delete the temporary folder {temp_dir} on {vm.name}: {e}")
