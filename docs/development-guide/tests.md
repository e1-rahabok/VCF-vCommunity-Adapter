# Tests

The pack is checked in three layers. Each catches a different kind of mistake. [CONTRIBUTING](../../CONTRIBUTING.md) says which to run after a change.

| Layer | Needs VCF Operations or vCenter? | What it catches | How to run it |
| :--- | :--- | :--- | :--- |
| **Unit tests** | No. They use fake data, see [`fakes.py`](../../Management%20Pack/tests/fakes.py) | A wrong formula or limit, a broken read function, a broken link in the docs | `python -m pytest tests`, from `Management Pack` |
| **KPI equivalence** | No | A KPI restructure that changes values it should not change | [KPI Equivalence Test](../../tools/equivalence/equivalence.md), when KPI code is restructured |
| **Live validation** | Yes, read-only, on the test instance | Whether the installed pack collects and its data lands on the vCenter objects | `pwsh tools/validate/validate.ps1` |

The unit tests test the code in the repository. The live validation tests the build **installed on the instance**, so it covers a code change only after that build is installed. [Tools](../../tools/README.md) gives the order of the steps.

## Unit tests

Code: [`Management Pack/tests/`](../../Management%20Pack/tests/)

Install the requirements and pytest, then run the tests from the `Management Pack` folder:

```
python -m pip install -r requirements.txt pytest
python -m pytest tests
```

`requirements.txt` does not include pytest, so install it as shown. Use Python 3.12: the SDK build tool in `requirements.txt` needs Python 3.9 to 3.12. The fake VCF Operations in `fakes.py` answers the Suite API calls from stored data, so no live system is needed. `tls_server.py` starts a local HTTPS server with a generated certificate for the TLS tests.

**Known issue: the two pinned-login tests can fail locally.** On some machines, `test_pinned_rest_login_sends_nothing_to_a_server_with_another_certificate` and `test_pinned_rest_login_reaches_a_server_with_the_pinned_certificate` in `test_library_collection.py` fail with `CERTIFICATE_VERIFY_FAILED`. They pass in CI. The cause is not known yet, and may be the local OpenSSL or urllib3 build. See finding N-01 in the [30 Oct 2026 Review](engineering-review/2026-10-30-review.md).

### CI

The CI workflow (`.github/workflows/ci.yml`) runs on every pull request and on every push to `main`, on Python 3.12. It installs `requirements.txt` plus pytest, ruff, bandit and pip-audit, and runs:

- the unit tests, which include the docs link check;
- `ruff` on `app` and `tests`, with the rules in `ruff.toml` at the repository root;
- `bandit`, a security scan of `app`;
- `pip-audit` on `adapter_requirements.txt`, the libraries that run in the container.

**Known gaps:**

- **`pip-audit` does not cover `requirements.txt`.** The build-time packages (the SDK build tool and its dependencies, such as `pillow` and `setuptools`) are not audited in CI. The engineering review found advisories on two of them (GOV-06, N-02).
- **The lint does not cover `tools/`.** Running `ruff check .` from the repository root reports six findings in the tools: four `zip()` calls without `strict=` in `tools/equivalence/planned_cases.py` (B905), and in `tools/importer/importer.py` an unused `dataclasses.field` import (F401) and a `raise` inside an `except` without `from` (B904). They are not part of the pack and don't affect the adapter. Fix them, then extend the CI lint to `tools`.

### Test files

| Test file | What it checks |
| :--- | :--- |
| `test_kpi_score.py` | The scoring, the batching of stats requests, and the tables of the KPIs in `KPI_MODULES`. It also checks that each of those KPIs calculates exactly the sub-metrics in its table, so a misspelt name fails. Cluster Consumption is not in `KPI_MODULES` yet. |
| `test_cluster_performance_metrics.py` | Cluster Performance formulas and worked examples. |
| `test_cluster_risk_metrics.py` | Cluster Risk formulas and worked examples. |
| `test_cluster_consumption_metrics.py` | Cluster Consumption formulas and a worked example. |
| `test_business_app_performance.py` | Tier, Business Application and Enterprise performance: the formulas, no data, namespaces within two levels, and a failed read. |
| `test_resource_pool_counts.py` | Number of Resource Pools and Cascading Resource Pools: nested levels and limits. |
| `test_vm_performance_metrics.py` | VM Performance formulas and worked examples. |
| `test_vm_guest_os_kpi.py` | VM Guest OS KPI: the average, and the fallback without VMware Tools. |
| `test_guest_os_performance_metrics.py` | Guest OS Performance formulas and worked examples. |
| `test_esxi_performance_metrics.py` | ESXi Performance formulas and worked examples. |
| `test_periodic_cluster_check.py` | Periodic Cluster Check: the schedule, the worst percent, the Close for Business rule, and which clusters are due. |
| `test_cluster_close_changes.py` | Cluster Delta Close and Open Counts: the direction of each change, blank values not counted, and the window. |
| `test_port_group_and_tools_counts.py` | Port groups per Datacenter (distributed and standard), the vSphere World sum, the 15-minute limit that only the port group count uses, and the VMware Tools counts, including powered-off VMs. |
| `test_cluster_summary_metrics.py` | vSphere World: worst and Worst 10 Percent cluster scores over the clusters of all vCenters. |
| `test_collection_health.py` | Collection health: only warnings and errors are counted, the first warning is kept and shortened, the log handler is removed after the cycle, the values go on the vCenter object only, and the keys match the alert definition. |
| `test_guest_collectors.py` | The Windows guest collectors, with a fake Guest API: the 5-minute timeout that stops a hung script, the back-off, the guest budget, a failed download, a service name with a comma, event levels, the event cap, and a failed temporary file. |
| `test_collection_steps.py` | A failed vCenter read raises instead of returning no objects, a container view is released after a failed read, a bad VM doesn't stop the VM loop, an unreadable configuration file doesn't discard the cycle, the Trust on First Use log messages, and which guest steps run for a VM, including when the guest budget is spent. |
| `test_shared_connection.py` | Five threads reading one shared vCenter content object: each call gets its own objects, and each view is released. It uses a fake, not a live vCenter. |
| `test_operational_availability.py` | Host and cluster Operational Availability: the bugs of the former super metric, N+0 to N+2, missing data, and the vSphere World summary. |
| `test_network_speed_degradation.py` | Network Speed Degradation: NIC by NIC, NICs that are down or have no configured speed, and the counts. |
| `test_vm_shares.py` | Share per vCPU and per MB: normal values, the former super metric's values, and no division by zero. |
| `test_ops_inventory.py` | Reading placement, power state, sizes, cores and threads from VCF Operations, and the Suite API endpoints used. |
| `test_guest_args.py` | Values from the configuration files that go into guest commands are checked, and unsafe ones are left out. |
| `test_guest_http.py` | The HTTPS calls of the guest file transfers, and their certificate check. |
| `test_tls.py` | The TLS modes of the vCenter connection, and the thumbprint checks. |
| `test_vcenter_certificate.py` | The Trust on First Use check of the vCenter certificate, and the report when it changes. |
| `test_config_files.py` | The lists read from the configuration files, the refusal of invalid XML, and problem texts that name the file. |
| `test_importer.py` | The bulk Adapter Instance importer: the TLS columns, and that every advanced setting is sent with the adapter's default. See [Importer](../../tools/importer/importer.md). |
| `test_relationship_update_mode.py` | The collection result uses the `PER_OBJECT` relationship mode, so Business Application memberships are kept. See [Business Application Performance](../reference/metrics/business-application-performance.md#membership-is-kept). |
| `test_library_collection.py` | Content Library and Library Item: items are children of their library, the library has no parent link, the metrics and properties, a failed read publishes nothing and logs a warning, the TLS mode of the REST connection, and the pinned login against a local HTTPS server. |
| `test_vm_template.py` | VM Template: built only for a VM marked as a template, with no parent link. |
| `test_docs_links.py` | Every link and image in the Markdown files resolves. It runs [`check_links.py`](../../tools/check-docs/check_links.py). |
| `test_submodule_imports.py` | The app code imports `concurrent.futures` by its full name. See [Submodule imports](#submodule-imports). |

When you add a KPI, add its test file and add it to `KPI_MODULES` in `test_kpi_score.py`. See [Metrics Code](metrics-code.md#how-to-add-a-kpi).

## Submodule imports

In the app code, import a submodule by its full name: `import concurrent.futures`, not `import concurrent`. A bare `import concurrent` binds only the package. `concurrent.futures` is then an attribute that exists only if another module has already imported it.

The unit tests can't catch this on their own. pytest loads the `anyio` plugin at start-up, and that plugin imports `concurrent.futures`, so the tests pass. In the container nothing else loads it, and the adapter fails with `AttributeError: module 'concurrent' has no attribute 'futures'`. Version 0.6.7 stopped collecting on the test instance because of this.

To see the failure, run this in a plain Python, without pytest:

```
python -c "import concurrent; concurrent.futures"
```

It fails with `AttributeError`. The same applies to any package whose submodules are used by name, such as `xml.etree` after a bare `import xml`.

`test_submodule_imports.py` fails when the app code has a bare `import concurrent`, or uses `concurrent.futures` without importing it. If a test passes and the instance fails with `has no attribute`, check the imports first.

## KPI equivalence

Code: [`tools/equivalence/`](../../tools/equivalence/). See [its page](../../tools/equivalence/equivalence.md).

When KPI code is restructured, its values must not change unless that is the intent. This test runs about 3,400 planned cases through two copies of the KPI code, before and after the change, and lists every difference in what they publish. It does not connect to anything.

## Live validation

Code: [`tools/validate/`](../../tools/validate/). See [its page](../../tools/validate/validate.md).

The unit tests can't show that the installed pack collects. The live validation reads the installed pack on the test instance and checks that its data is on the vCenter objects. It is read-only. It exits with 0 on a pass and 1 on any failure. Warnings are shown but don't fail the run.

## Documentation links

`check_links.py` checks every relative link and image in the Markdown files, including heading anchors. It does not check web links. Run it before a commit that changes documentation:

```
python tools/check-docs/check_links.py
```

## Limitations

- **The unit tests check the code against expected values that someone wrote.** A wrong expected value passes. The worked examples on each KPI page are the reference for those values.
- **The live validation depends on the instance.** It can't cover a configuration that the instance doesn't have.
- **Nothing tests the UI.** Dashboards and reports are imported as files and checked by looking at them on the instance.
