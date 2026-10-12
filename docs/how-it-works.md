# How It Works

**On this page:**

- [How the vCommunity Management Pack Works](#how-the-vcommunity-management-pack-works)
- [How the Integration SDK Works](#how-the-integration-sdk-works)

---

## How the vCommunity Management Pack Works

Custom Management Packs created using the VCF Operations Integration SDK have some additional requirements. First, their Adapter Instances need to run on a **Cloud Proxy** for data collection.

Once you've installed the Management Pack and created an Adapter Instance, the Cloud Proxy pulls the adapter's Docker image from the container registry. That image installs the files defined in its `Dockerfile`, and the PAK file is then initialized to begin the data collection process.

![vCommunity Adapter Topology](images/vCommunity-Adapter-Topology.svg)

If the Cloud Proxy has container registry access (i.e. access to the Internet), users can simply install the Management Pack and create Adapter Instances — no further modification is needed in VCF Operations.

> If your Cloud Proxy does **not** have internet/registry access, see [Dark Site Installation](dark-site.md) instead.

---

## No stale values

Most of the pack's metrics are calculated from stats that VCF Operations already holds, read with its "latest" query. That query returns the last stored value **however old it is**: a host that is down or disconnected, or a VM that is powered off, keeps its last value as "latest".

The pack never uses such a value. A metric showing blank is better than one showing wrong data.

- **Stats** older than 10 minutes (two 5-minute collection cycles) are treated as **no data**. A metric that depends on them is not published for that cycle, and shows blank.
- **Properties** keep their last known value. VCF Operations stores a property only when it changes, so its last value is its current value.
- Two cycles, not one, so that a single late collection does not blank everything.
- The limit is `STALE_AFTER_MINUTES` in [`utils/ops_stats.py`](../Management%20Pack/app/utils/ops_stats.py).

> **Known limitation.** If the VMware vCenter adapter in VCF Operations is set to collect less often than every 10 minutes, every metric of this pack that depends on its stats is blank.

---

## How the Integration SDK Works

A Cloud Proxy runs a collector process that manages adapter containers, one per Adapter Instance. Within each container is a REST server and the adapter process itself. The `Commands.cfg` file tells the REST server how to run the adapter process for each endpoint (`test`, `collect`, `adapter_definition`, etc.).

![VCF Operations Integration SDK Topology](images/VCF-Operations-Integration-SDK-Topology.png)

---

**Next:** [Metrics & Properties Reference](metrics-reference.md) · [Configuration](configuration.md)
