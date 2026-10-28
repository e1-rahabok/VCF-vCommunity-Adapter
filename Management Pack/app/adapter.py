#  Copyright 2026 VCF Operations vCommunity Management Pack
#  Author: Onur Yuzseven onur.yuzseven@broadcom.com

#import os
import sys
#import threading
import time
import json
import atexit
import xml.etree.ElementTree as ET
import concurrent
import constants.main
import aria.ops.adapter_logging as logging
from typing import Any
from typing import List
from typing import Optional
from collections import defaultdict
from aria.ops.adapter_instance import AdapterInstance
from aria.ops.definition.adapter_definition import AdapterDefinition
from aria.ops.object import Object
from aria.ops.result import CollectResult
from aria.ops.result import EndpointResult
from aria.ops.result import TestResult
from aria.ops.suite_api_client import key_to_object
from aria.ops.suite_api_client import SuiteApiClient
from aria.ops.timer import Timer
from pyVim.connect import Disconnect
from pyVim.connect import SmartConnect
from utils import config_files
from utils import guest_args
from utils import guest_http
from utils import tls
from collectors.cluster.collectClusterData import collect_cluster_data
from collectors.host.collectHostData import collect_host_data
from collectors.vm.collectVMData import collect_vm_data
from collectors.datastore.collectDatastoreData import collect_datastore_data
from collectors.vcenter.collectvCenterData import collect_vcenter_data
from collectors.world.collectWorldData import collect_world_data
from collectors.datacenter.collectDatacenterData import collect_datacenter_data
from metrics.cluster import cluster_risk_metrics, periodic_cluster_check
from definition import get_adapter_definition
from utils import collection_health
from metrics.vcenter.vcenter_availability import read_operational_availability
from metrics.vcenter.vcenter_network_speed import read_network_speed

logger = logging.getLogger(__name__)
timingLogger = logging.getLogger("[CollectionResult]")


def get_win_service_configFile(adapter_instance: AdapterInstance) -> str:
    win_service_config_file = adapter_instance.get_identifier_value("win_service_config_file")
    return win_service_config_file

def get_win_event_configFile(adapter_instance: AdapterInstance) -> str:
    configFile = adapter_instance.get_identifier_value("win_event_config_file")
    return configFile

def get_esxi_adv_settings_configFile(adapter_instance: AdapterInstance) -> str:
    esxiAdvSettingsConfigFile = adapter_instance.get_identifier_value("esxi_adv_settings_config_file")
    return esxiAdvSettingsConfigFile

def get_esxi_vib_driver_configFile(adapter_instance: AdapterInstance) -> str:
    esxi_vib_driver_config_file = adapter_instance.get_identifier_value("esxi_vib_driver_config_file")
    return esxi_vib_driver_config_file

def get_vm_adv_settings_configFile(adapter_instance: AdapterInstance) -> str:
    vm_adv_settings_config_file = adapter_instance.get_identifier_value("vm_adv_settings_config_file")
    return vm_adv_settings_config_file

def get_vm_configuration_configFile(adapter_instance: AdapterInstance) -> str:
    vm_configuration_config_file = adapter_instance.get_identifier_value("vm_configuration_config_file")
    return vm_configuration_config_file

def get_winCredential(adapter_instance: AdapterInstance) -> str:
    username = adapter_instance.get_credential_value("winUser")
    password = adapter_instance.get_credential_value("winPass")
    return username, password

def getServiceMonitoringStatus(adapter_instance: AdapterInstance) -> str:
    serviceMonitoringStatus = adapter_instance.get_identifier_value("serviceMonitoring")
    return serviceMonitoringStatus

def getWindowsEventLogMonitoringStatus(adapter_instance: AdapterInstance) -> str:
    WindowsEventLogMonitoringStatus = adapter_instance.get_identifier_value("winEventMonitoring")
    return WindowsEventLogMonitoringStatus    

def get_config_file_data(adapter_instance: AdapterInstance, configFile, problems: List[str]) -> List[str]:
    """The items of one configuration file. A file that cannot be read, or is not valid XML, gives [] for that file
    only, and its problem is added to problems. See utils/config_files.py."""
    apiPath = f"api/configurations/files?path=SolutionConfig/{configFile}.xml"

    with adapter_instance.suite_api_client as suite_api:
        getConfigFile = suite_api.get(url=apiPath)

    if not getConfigFile.ok:
        problems.append(config_files.missing_problem(configFile, getConfigFile.status_code))
        logger.warning(problems[-1])
        return []

    try:
        return config_files.parse_list(getConfigFile.text)
    except ET.ParseError as e:
        problems.append(config_files.invalid_problem(configFile, e.msg))
        logger.error(problems[-1])
        return []


TIMINGS = defaultdict(list)

def record_timing(operationName, duration):
    TIMINGS[operationName].append(duration)


def timingSummary():
    total = 0
    timingLogger.info("====================== Collection Timing Summary ======================")

    for operationName, duration_list in TIMINGS.items():
        if not duration_list:
            continue

        currentDuration = sum(duration_list)
        total += currentDuration
        
        if currentDuration < 60:
            timingLogger.info(f"Collection Operation: {operationName} > Duration: {currentDuration:.2f} seconds.")
        else:
            minutes = currentDuration / 60
            timingLogger.info(f"Collection Operation: {operationName} > Duration: {minutes:.2f} minutes.")

    timingLogger.info("=======================================================================")
    
    if total < 60:
        timingLogger.info(f"Total Collection Duration: {total:.2f} seconds.")
    else:
        total_minutes = total / 60
        timingLogger.info(f"Total Collection Duration: {total_minutes:.2f} minutes.")
        
    timingLogger.info("=======================================================================")


def test(adapter_instance: AdapterInstance) -> TestResult:
    with Timer(logger, "Test connection"):
        result = TestResult()
        try:
            logger.debug(f"Returning test result: {result.get_json()}")

            service_instance = _get_service_instance(adapter_instance)
            content = service_instance.RetrieveContent()
            logger.info(f"content: {content}")

        except Exception as e:
            logger.error("Unexpected connection test error")
            logger.exception(e)
            result.with_error("Unexpected connection test error: " + repr(e))
        finally:
            return result


def collect(adapter_instance: AdapterInstance) -> CollectResult:
    with Timer(logger, "Collection"):
        result = CollectResult()
        # Counts the warnings and errors of this cycle, for the Collection Warnings alert. See utils/collection_health.py.
        warnings = collection_health.start()
        try:
            start_time = time.perf_counter()
            service_instance = _get_service_instance(adapter_instance)
            content = service_instance.RetrieveContent()
            # The certificate vCenter presents now, for the Trust on First Use comparison on the vCenter object
            # (properties/vcenter/certificate.py). Read in every mode, so the thumbprint is always visible.
            vcenter_certificate = tls.presented_thumbprint(
                adapter_instance.get_identifier_value(constants.main.HOST_IDENTIFIER),
                int(adapter_instance.get_identifier_value(constants.main.PORT_IDENTIFIER, 443)),
            )
            guest_http.configure(adapter_instance.get_identifier_value(constants.main.GUEST_TLS_VALIDATION))
            ServiceMonitoringStatus = getServiceMonitoringStatus(adapter_instance)
            WindowsEventLogMonitoringStatus = getWindowsEventLogMonitoringStatus(adapter_instance)
            winUser, winPassword = get_winCredential(adapter_instance)

            # Problems with the configuration files. Each one is published as an event on the vCenter object.
            config_problems: List[str] = []

            windowsEventConfigFile = get_win_event_configFile(adapter_instance)
            apiPath = f"api/configurations/files?path=SolutionConfig/{windowsEventConfigFile}.xml"
            with adapter_instance.suite_api_client as suite_api:
                getConfigFile = suite_api.get(url = apiPath)

            # The event list is passed to the Windows guest as it is, so it is checked here, not parsed.
            winEventLogConfigFile = ""
            if not getConfigFile.ok:
                config_problems.append(config_files.missing_problem(windowsEventConfigFile, getConfigFile.status_code))
                logger.warning(config_problems[-1])
            else:
                reason = config_files.check_xml(getConfigFile.text)
                if reason is None:
                    winEventLogConfigFile = getConfigFile.text
                else:
                    config_problems.append(config_files.invalid_problem(windowsEventConfigFile, reason))
                    logger.error(config_problems[-1])

            windowsServiceConfigFile = get_win_service_configFile(adapter_instance)
            windowsServices = guest_args.safe_service_names(
                get_config_file_data(adapter_instance, windowsServiceConfigFile, config_problems))

            esxiAdvSettingsConfigFile = get_esxi_adv_settings_configFile(adapter_instance)
            esxiAdvSettings = get_config_file_data(adapter_instance, esxiAdvSettingsConfigFile, config_problems)

            esxiVIBDriverConfigFile = get_esxi_vib_driver_configFile(adapter_instance)
            esxiVIBDrivers = get_config_file_data(adapter_instance, esxiVIBDriverConfigFile, config_problems)

            vmAdvParametersConfigFile = get_vm_adv_settings_configFile(adapter_instance)
            vmAdvParameters = get_config_file_data(adapter_instance, vmAdvParametersConfigFile, config_problems)

            vmConfigurationConfigFile = get_vm_configuration_configFile(adapter_instance)
            vmConfigs = get_config_file_data(adapter_instance, vmConfigurationConfigFile, config_problems)

            with adapter_instance.suite_api_client as client:
                adapter_instance_id = _get_vcenter_adapter_instance_id(
                    client, adapter_instance
                )
                if adapter_instance_id is None:
                    result.with_error(
                        f"No vCenter Adapter Instance found matching vCenter Server '{adapter_instance.get_identifier_value(constants.main.HOST_IDENTIFIER)}'"
                    )
                    return result
                
                duration = time.perf_counter() - start_time
                record_timing("main_collect", duration)

                # Operational Availability of the hosts and clusters of this vCenter. Read once here, because the
                # host, cluster and vCenter collections below all publish part of it.
                availability = read_operational_availability(client, adapter_instance_id)
                # Network Speed Degradation of the hosts of this vCenter, for the host and Datacenter collections.
                network_speed = read_network_speed(client, adapter_instance_id)

                start_times = {}

                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as data_executor:
                    
                    # 1. Cluster feature definition
                    start_times["collect_cluster_data"] = time.perf_counter()
                    future_cls = data_executor.submit(
                        collect_cluster_data, client, adapter_instance_id, result, content, availability,
                        adapter_instance.get_identifier_value(periodic_cluster_check.TIME_SETTING),
                        adapter_instance.get_identifier_value(periodic_cluster_check.PERIOD_SETTING),
                        cluster_risk_metrics.monster_vm_size(
                            adapter_instance.get_identifier_value(cluster_risk_metrics.MONSTER_CPU_SETTING),
                            adapter_instance.get_identifier_value(cluster_risk_metrics.MONSTER_MEMORY_SETTING),
                            adapter_instance.get_identifier_value(cluster_risk_metrics.MONSTER_MEMORY_MIN_SETTING),
                        ),
                        adapter_instance.get_identifier_value(periodic_cluster_check.WORST_PERCENT_SETTING),
                    )

                    # 2. Host feature definition
                    start_times["collect_host_data"] = time.perf_counter()
                    future_host = data_executor.submit(
                        collect_host_data, client, adapter_instance_id, result, content, esxiAdvSettings, esxiVIBDrivers,
                        availability, network_speed
                    )

                    # 3. VM feature definition
                    start_times["collect_vm_data"] = time.perf_counter()
                    future_vm = data_executor.submit(
                        collect_vm_data, client, adapter_instance_id, result, content, 
                        ServiceMonitoringStatus, WindowsEventLogMonitoringStatus, winUser, winPassword, 
                        winEventLogConfigFile, vmConfigs, vmAdvParameters, windowsServices
                    )

                    # 4. Datastore feature definition
                    start_times["collect_datastore_data"] = time.perf_counter()
                    future_ds = data_executor.submit(
                        collect_datastore_data, client, adapter_instance_id, result, content
                    )

                    # 5. vCenter feature definition
                    start_times["collect_vcenter_data"] = time.perf_counter()
                    future_vc = data_executor.submit(
                        collect_vcenter_data, client, adapter_instance_id, result, content, availability,
                        vcenter_certificate,
                        adapter_instance.get_identifier_value(constants.main.HOST_IDENTIFIER),
                        config_problems,
                    )

                    # 6. vSphere World: cluster summary metrics, over the clusters of all vCenters
                    start_times["collect_world_data"] = time.perf_counter()
                    future_world = data_executor.submit(
                        collect_world_data, client, result,
                        adapter_instance.get_identifier_value(periodic_cluster_check.TIME_SETTING),
                        adapter_instance.get_identifier_value(periodic_cluster_check.PERIOD_SETTING),
                    )

                    # 7. Datacenter: Total Network Speed Degradation of this vCenter's Datacenters
                    start_times["collect_datacenter_data"] = time.perf_counter()
                    future_dc = data_executor.submit(collect_datacenter_data, client, adapter_instance_id, result, network_speed)

                    # Define main futures
                    main_futures = [future_cls, future_host, future_vm, future_ds, future_vc, future_world, future_dc]
    
                    for future in concurrent.futures.as_completed(main_futures):
                        # Check future function
                        if future == future_cls:
                            func_name = "collect_cluster_data"
                        elif future == future_ds:
                            func_name = "collect_datastore_data"
                        elif future == future_vc:
                            func_name = "collect_vcenter_data"
                        elif future == future_host:
                            func_name = "collect_host_data"
                        elif future == future_world:
                            func_name = "collect_world_data"
                        elif future == future_dc:
                            func_name = "collect_datacenter_data"
                        else:
                            func_name = "collect_vm_data"

                        try:
                            future.result()
                            duration = time.perf_counter() - start_times[func_name]
                            record_timing(func_name, duration)
                            
                            logger.info(f"Finished {func_name} collection successfully.")
                            
                        except Exception as exc:
                            logger.error(f"Main data collection thread error in {func_name}: {exc}")
                            
                logger.info(f"Finished total data collection.")
                collection_health.publish(result.objects.values(), warnings)

        except Exception as e:
            logger.error("Unexpected collection error")
            logger.exception(e)
            result.with_error("Unexpected collection error: " + repr(e))
        finally:
            collection_health.stop(warnings)
            timingSummary()
            return result


def get_endpoints(adapter_instance: AdapterInstance) -> EndpointResult:
    with Timer(logger, "Get Endpoints"):
        result = EndpointResult()
        logger.debug(f"Returning endpoints: {result.get_json()}")
        return result


def _get_service_instance(
    adapter_instance: AdapterInstance,
) -> Any:
    host = adapter_instance.get_identifier_value(constants.main.HOST_IDENTIFIER)
    port = int(adapter_instance.get_identifier_value(constants.main.PORT_IDENTIFIER, 443))
    user = adapter_instance.get_credential_value(constants.main.USER_CREDENTIAL)
    password = adapter_instance.get_credential_value(constants.main.PASSWORD_CREDENTIAL)

    tls_args = tls.vcenter_connect_args(
        adapter_instance.get_identifier_value(constants.main.VCENTER_TLS_VALIDATION),
        adapter_instance.get_identifier_value(constants.main.VCENTER_THUMBPRINT),
    )

    try:
        service_instance = SmartConnect(host=host, port=port, user=user, pwd=password, **tls_args)
    except Exception as exc:
        explanation = tls.explain_connect_error(exc, host)
        if explanation:
            raise ConnectionError(explanation) from exc
        raise

    atexit.register(Disconnect, service_instance)

    return service_instance


def _get_vcenter_adapter_instance_id(
    client: SuiteApiClient, adapter_instance: Object
) -> Optional[str]:
    ais: List[Object] = client.query_for_resources(
        {
            "adapterKind": [constants.main.VCENTER_ADAPTER_KIND],
            "resourceKind": ["VMwareAdapter Instance"],
        }
    )
    vcenter_server = adapter_instance.get_identifier_value(constants.main.HOST_IDENTIFIER)
    for ai in ais:
        logger.debug(
            f"Considering vCenter Adapter Instance with VCURL: {ai.get_identifier_value('VCURL')}"
        )
        if ai.get_identifier_value("VCURL") == vcenter_server:
            return _get_adapter_instance_id(client, ai)
    return None


def _get_adapter_instance_id(
    client: SuiteApiClient, adapter_instance: Object
) -> Optional[Any]:
    response = client.get(
        f"api/adapters?adapterKindKey={adapter_instance.get_key().adapter_kind}"
    )
    if response.status_code < 300:
        for ai in json.loads(response.content).get("adapterInstancesInfoDto", []):
            adapter_instance_key = key_to_object(ai.get("resourceKey")).get_key()
            if adapter_instance_key == adapter_instance.get_key():
                return ai.get("id")
    return None


def main(argv: List[str]) -> None:
    logging.setup_logging("adapter.log")
    logging.rotate()
    logger.info(f"Running adapter code with arguments: {argv}")
    if len(argv) != 3:
        logger.error("Arguments must be <method> <inputfile> <ouputfile>")
        exit(1)

    method = argv[0]

    if method == "test":
        test(AdapterInstance.from_input()).send_results()
    elif method == "endpoint_urls":
        get_endpoints(AdapterInstance.from_input()).send_results()
    elif method == "collect":
        collect(AdapterInstance.from_input()).send_results()
    elif method == "adapter_definition":
        result = get_adapter_definition()
        if type(result) is AdapterDefinition:
            result.send_results()
        else:
            logger.info(
                "get_adapter_definition method did not return an AdapterDefinition"
            )
            exit(1)
    else:
        logger.error(f"Command {method} not found")
        exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])