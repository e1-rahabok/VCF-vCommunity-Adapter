# Tests

The pack is checked in three layers. Each one catches a different kind of mistake, and the contributor guide in [CONTRIBUTING](../../CONTRIBUTING.md) says which to run after a change.

| Layer | Needs VCF Operations or vCenter? | What it catches | Run it |
| :--- | :--- | :--- | :--- |
| **Unit tests** | No. Fake data, see [`fakes.py`](../../Management%20Pack/tests/fakes.py) | A wrong formula, a wrong limit, a broken reading function, a broken link in the docs | `python -m pytest tests`, from `Management Pack` |
| **KPI equivalence** | No | A change to KPI code that changes a value it should not change | [Equivalence test](../../tools/equivalence/equivalence.md), when the KPI code is restructured |
| **Live validation** | Yes, read-only, on the test instance | The pack as installed on the instance collects, and its data lands on the vCenter objects | `pwsh tools/validate/validate.ps1` |

The unit tests test the code in this repository. The live validation tests the build *installed on the instance*. A change in the code is covered by the live validation only after that build is installed. See [Tools](../../tools/README.md) for the order of the steps.

## Unit tests

Code: [`Management Pack/tests/`](../../Management%20Pack/tests/)

Run them from the `Management Pack` folder:

```
python -m pytest tests
```

They need the Python requirements of the repository (`requirements.txt`). The fake VCF Operations in `fakes.py` answers the Suite API calls with stored data, so the tests run without a live system. `tls_server.py` starts a local HTTPS server with a generated certificate, for the TLS tests.

| Test file | What it checks |
| :--- | :--- |
| `test_kpi_score.py` | The scoring, the batching of the stats requests, and the tables of every KPI. It also checks that each KPI calculates exactly the sub-metrics in its table, so a misspelt name cannot slip through. |
| `test_cluster_performance_metrics.py` | Cluster Performance formulas and worked examples. |
| `test_cluster_risk_metrics.py` | Cluster Risk formulas and worked examples. |
| `test_cluster_consumption_metrics.py` | Cluster Consumption formulas and a worked example. |
| `test_resource_pool_counts.py` | Number of Resource Pools and Cascading Resource Pools: the levels of the lab tree, and the limits. |
| `test_vm_performance_metrics.py` | VM Performance formulas and worked examples. |
| `test_vm_guest_os_kpi.py` | VM Guest OS KPI: the average, and the fallback without VMware Tools. |
| `test_guest_os_performance_metrics.py` | Guest OS Performance formulas and worked examples. |
| `test_esxi_performance_metrics.py` | ESXi Performance formulas and worked examples. |
| `test_periodic_cluster_check.py` | Periodic Cluster Check: the schedule, the worst percent, the Close for Business rule, and which clusters are due. |
| `test_cluster_close_changes.py` | Cluster Delta Close and Open Count: the direction of each change, blank values not counted, and the window. |
| `test_port_group_and_tools_counts.py` | Port groups per Datacenter (distributed and standard), the vSphere World sum, the 15-minute limit used only by the port group count, and the VMware Tools counts, including powered-off VMs. |
| `test_cluster_summary_metrics.py` | vSphere World: Bottom 10 Percent and worst cluster scores, over the clusters of all vCenters. |
| `test_operational_availability.py` | Host and cluster Operational Availability: the super-metric bugs, N+0 to N+2, missing data, and the vSphere World summary. |
| `test_network_speed_degradation.py` | Network Speed Degradation: NIC by NIC, NICs that are down or have no configured speed, and the counts. |
| `test_vm_shares.py` | Share per vCPU and per MB: normal values, the super metric's values, and no division by zero. |
| `test_ops_inventory.py` | Reading placement, power state, sizes, cores and threads from VCF Operations, and the Suite API endpoints used. |
| `test_guest_args.py` | The values from the configuration files that go into guest commands are checked, and unsafe ones are left out. |
| `test_guest_http.py` | The HTTPS calls of the guest file transfers, and their certificate check. |
| `test_tls.py` | The TLS modes of the vCenter connection, and the thumbprint checks. |
| `test_vcenter_certificate.py` | The Trust on First Use check of the vCenter certificate, and the report when it changes. |
| `test_config_files.py` | The lists read from the configuration files, the refusal of invalid XML, and the problem texts that name the file. |
| `test_importer.py` | The bulk Adapter Instance importer, see [Importer](../../tools/importer/importer.md). |
| `test_docs_links.py` | Every link and image in the Markdown files resolves. It runs [`check_links.py`](../../tools/check-docs/check_links.py). |

When you add a KPI, add its test file and its entry in `KPI_MODULES` of `test_kpi_score.py`. See [Metrics Code](metrics-code.md#how-to-add-a-kpi).

## KPI equivalence

Code: [`tools/equivalence/`](../../tools/equivalence/). See [its page](../../tools/equivalence/equivalence.md).

When the code of a KPI is restructured, its values must not change, unless that is the intent. This test runs about 3,400 planned cases through two copies of the KPI code, before and after the change, and lists every difference in what they publish. It does not connect to anything.

## Live validation

Code: [`tools/validate/`](../../tools/validate/). See [its page](../../tools/validate/validate.md).

The unit tests cannot show that the installed pack collects. The live validation reads the installed pack, on the test instance, and checks that its data is on the vCenter objects. It is read-only. It exits with 0 on a pass and 1 on any failure. Warnings are shown but do not fail the run.

## Documentation links

`check_links.py` checks every relative link and image in the Markdown files, and every heading anchor. It does not connect to the web. Run it before a commit that changes documentation:

```
python tools/check-docs/check_links.py
```

## Limitations

- **The unit tests check the code against the expected values that someone wrote.** A wrong expected value passes. The worked examples in each KPI page are the reference for those values.
- **The live validation depends on the instance.** A test that passes on one instance may not cover a configuration that the instance does not have.
- **Nothing tests the UI.** The dashboards and reports are imported as files, and are checked by looking at them on the instance.
