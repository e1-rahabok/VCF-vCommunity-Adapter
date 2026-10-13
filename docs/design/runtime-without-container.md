# Running Without the Container — Planning

> **Status: planned, not built.** This page records options for future work, so that collaborators know what was studied and what is recommended. Nothing on this page exists in the pack yet, and nothing changes for now.

## Goal

The pack is built with the VCF Operations Integration SDK. Its code runs in a **container on the Cloud Proxy**, pulled from a container registry (today `ghcr.io/e1-rahabok/vcf-operations-vcommunity`). At some customer sites this is a problem.

This page lists the workarounds, and the option of a native Java adapter, which removes the container.

## Decisions already made

| Topic | Decision |
| :--- | :--- |
| For now | No change. The pack stays a Python containerized adapter. |
| Language | Python stays, unless every container workaround below is blocked at a site. The language does not limit speed: the time is spent waiting for vCenter and VCF Operations, and the pack already reads them in bulk. |
| Java port | Not started. If it is done, it starts from this repository, not from the vmbro original. See [Java port](#option-6-native-java-adapter-java-port). |

## Which problem, which option

| Problem at the site | Option |
| :--- | :--- |
| Cloud Proxy has no internet (dark site) | [1. Private registry](#option-1-private-registry), [2. Pak per customer](#option-2-pak-per-customer-registry) |
| Public registry (ghcr.io) not allowed | [1](#option-1-private-registry), [2](#option-2-pak-per-customer-registry) |
| Cloud Proxy resources | [3. Sizing](#option-3-cloud-proxy-sizing) |
| Security policy on containers | [4. Hardened image](#option-4-hardened-image) |
| No custom container allowed at all | [5. External collector](#option-5-external-collector-no-adapter), [6. Java](#option-6-native-java-adapter-java-port) |

## Option 1: Private registry

- Copy the image into the customer's internal registry (Harbor, Artifactory, ...), and point the pack at it.
- Already documented: [Dark Site Installation](../how-to/dark-site-installation.md). Pull, re-tag, push, set `REGISTRY` in `vCommunity.conf` on each node, restart the collector.
- **Limitation:** a manual step per site, repeated for every new version of the pack.

## Option 2: Pak per customer registry

- Build the pak with the customer's registry in it (`mp-build -r <customer registry>`), and push the image there.
- Nothing to edit on the VCF Operations nodes.
- **Limitation:** one pak per customer registry to build and keep track of.

## Option 3: Cloud Proxy sizing

- The container runs one Python process per account. The code reads in bulk, so the load is light.
- If it is still too much: fewer accounts per Cloud Proxy, or a dedicated Cloud Proxy for this pack.

## Option 4: Hardened image

For a security review of the container:

- Build only on the Broadcom base image, with a pinned requirements list.
- Scan the image (Trivy, Grype) and give the report to the customer.
- Sign the image (cosign), if the customer's registry checks signatures.
- **Limitation:** some customers do not allow any custom container. Then only option 5 or 6 helps.

## Option 5: External collector (no adapter)

Most of the pack reads from VCF Operations and writes back to it: the KPIs, Operational Availability, Network Speed Degradation, VM Shares, the vSphere World metrics and the Daily Cluster Check. Only the configuration properties read vCenter.

- Run that code outside VCF Operations, as a plain Python job every 5 minutes on a small Linux VM (cron or systemd).
- It writes the same metrics with the Suite API, on the same objects, with the same keys. The dashboards do not change.
- The pak holds only content: dashboards, views, reports. No container, nothing on the Cloud Proxy.
- About 90 % of the code stays. Only the input and output layer changes.

**Limitations:**

- One more VM to run and patch.
- The credentials are kept on that VM, not in the account UI of VCF Operations.
- No adapter status in VCF Operations. The job needs its own monitoring.

## Option 6: Native Java adapter (Java port)

A Java adapter runs inside the VCF Operations collector: no container, no registry, less load on the Cloud Proxy, simpler dark-site installs.

### Existing ports, by sentania-labs

Studied in October 2026. They are ports of the **vmbro original**, not of this repository.

| Repository | Content | State |
| :--- | :--- | :--- |
| [vcf-content-factory-sdk-vcommunity](https://github.com/sentania-labs/vcf-content-factory-sdk-vcommunity) | Full port (vSphere and Windows guest OS), adapter kind `vcfcf_vcommunity` | Version 1.0.0 build 11, not released. The author says it is out of date. |
| [vcf-content-factory-sdk-vcommunity-vsphere](https://github.com/sentania-labs/vcf-content-factory-sdk-vcommunity-vsphere) | Cluster, host and VM configuration; 37 super metrics, 12 dashboards, 11 reports | Build 13. The builds since the split changed content and docs, not the collection. |
| [vcf-content-factory-sdk-vcommunity-os](https://github.com/sentania-labs/vcf-content-factory-sdk-vcommunity-os) | Windows services, OS information and event logs | Build 1. Shelved: Windows guest operations return no data on hardened Windows Server 2025 domain controllers (the Python original has the same problem there). |

Splitting vSphere from the Windows guest OS is a good choice: a failure in one does not affect the other.

The author has offered to resync the port.

### Issues found in the existing ports

- **One vCenter call per value.** Each property of each object is a separate `RetrieveProperties` call, one after the other: about 15 per cluster, 5 or more per VM. A missing value is retried with shorter paths, adding more calls. This pack reads all objects of a type in one call.
- **An extra check before most reads.** `ensureConnected()` sends a `CurrentTime` call first, which about doubles the calls.
- **Two Suite API writes per object.** 10,000 VMs mean 20,000 requests per cycle.
- **Estimate:** at 5,000 VMs, 17 to 40 minutes per cycle, for a 5-minute cycle. Estimated from the code, not measured.
- **Inventory capped at 10,000 per object type** (`pageSize=10000`, no paging).
- **Windows guest operations run one VM at a time**, with up to 120 s per VM.
- **Not verified on a live system:** Suite API access from a remote collector or Cloud Proxy, licensing, VIB packages, the credential dialog.
- **Windows events become numbered properties** (`Last Event|1`, `|2`, ...), whose numbers change between cycles.
- **Build dependencies:** the Broadcom Java SDK jar (`vrops-adapters-sdk-2.2.jar`), which is not public and is copied from an appliance, and the sentania-labs framework jar and build kit.

### What a port of this pack needs

- None of the code of this pack is in the existing ports: the 5 KPIs, Operational Availability, Network Speed Degradation, VM Shares, the vSphere World metrics, the Daily Cluster Check. Their content still uses the super metrics this pack replaced with code.
- This pack reads 5-minute data back from VCF Operations. The Java adapter must read the Suite API from the collector too, which is not verified from a Cloud Proxy.
- Two code bases, Python and Java, drift apart: every change has to be made twice, unless Python is retired.

### Conditions for a resync

1. **Bulk vCenter reads:** one property-collector call per object type with all the paths needed, paged.
2. **Bulk Suite API writes:** many objects per request.
3. **Paged inventory:** no 10,000 cap.
4. **Scale test:** a full cycle under 5 minutes at 2,000 clusters and the matching number of VMs.
5. **This repository as the base:** port the code, not the old super metrics. Keep the metric keys, so the dashboards keep working.
6. **Proof first** that Suite API reads work from a Cloud Proxy collector, before the KPIs are ported.

## Recommendation

- Dark site or public registry: option 2 (pak per customer registry), or option 1. The smallest change.
- No custom container allowed: option 5 before option 6. Much less work, and the code stays in Python.
- Option 6 only when options 1 to 5 are all blocked at the sites that matter, and with the conditions above.
