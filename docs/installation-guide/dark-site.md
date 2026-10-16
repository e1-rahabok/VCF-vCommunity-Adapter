# Dark Site Installation

This document describes a workaround for environments where Cloud Proxies have no internet access, by pulling the VCF Operations vCommunity MP container image manually and pushing it to a private registry.

> **Do you actually need this?** If your Cloud Proxy already has internet access to pull the container image, you don't need this workaround — once the Adapter Instance is configured, the Cloud Proxy will automatically pull the image on its own. See [How It Works](how-it-works.md) for the normal (internet-connected) flow.

**On this page:**

- [Step 1–4: On the Local Machine](#step-14-on-the-local-machine)
- [Step 5: On Each VCF Operations Cluster Node](#step-5-on-each-vcf-operations-cluster-node-excluding-cloud-proxies)
- [Step 6: On Each Cloud Proxy](#step-6-on-each-cloud-proxy)

---

## Step 1–4: On the Local Machine

The Cloud Proxy pulls the image named in `vCommunity.conf`, which is inside the PAK file. It joins three fields, and pulls by digest, not by tag:

| Field | Value in 0.2.0 |
| :--- | :--- |
| `REGISTRY` | `ghcr.io` |
| `REPOSITORY` | `/e1-rahabok/vcf-operations-vcommunity` |
| `DIGEST` | `sha256:673e168b3791f22c4d732d541b6e9dc3170b985b6d33f7e89d293d53cda5a909` |

So in your private registry, keep the same repository path and the same digest. Only the registry changes, in Step 5.

**Step 1: Find the image for your PAK version.**

The images are listed on GitHub:

```
https://github.com/users/e1-rahabok/packages/container/package/vcf-operations-vcommunity
```

Tags are `<version>_<build time>`. For 0.2.0, use `0.2.0_1792160496.3382835`. For another version, use the tag whose digest matches `DIGEST` in that PAK file's `vCommunity.conf`. Replace the tag in the commands below.

**Step 2: Pull the image to your local machine.**

```bash
docker pull ghcr.io/e1-rahabok/vcf-operations-vcommunity:0.2.0_1792160496.3382835
```

**Step 3: Re-tag the image for your private registry.**

> Replace `private-registry.local.network` with your own registry's FQDN in every command below. Keep the path `e1-rahabok/vcf-operations-vcommunity`: it must match `REPOSITORY`.

```bash
docker tag ghcr.io/e1-rahabok/vcf-operations-vcommunity:0.2.0_1792160496.3382835 private-registry.local.network/e1-rahabok/vcf-operations-vcommunity:0.2.0_1792160496.3382835
```

**Step 4: Push the image to your private registry.**

```bash
docker push private-registry.local.network/e1-rahabok/vcf-operations-vcommunity:0.2.0_1792160496.3382835
```

`docker push` prints a digest at the end. It must equal `DIGEST`. If it does not, the Cloud Proxy cannot find the image: copy the image with a tool that keeps the digest, such as `skopeo copy` or `crane copy`.

---

## Step 5: On Each VCF Operations Cluster Node (excluding Cloud Proxies)

Edit the `REGISTRY` field in `vCommunity.conf` on every node:

```
$VCOPS_BASE/user/plugins/inbound/vCommunity.conf
```

```
REGISTRY=private-registry.local.network
```

---

## Step 6: On Each Cloud Proxy

Restart the collector so it picks up the new registry setting:

```bash
service collector restart
```

---

Once steps 1–6 are complete, proceed with [Adapter Instance configuration](../configuration-guide/adapter-instance.md) as normal — the container image will now be pulled from your private registry (`private-registry.local.network`) instead of the public one.

---

> Other options for sites where the container is a problem: [Running Without the Container](https://github.com/e1-rahabok/VCF-vCommunity-Adapter/issues/4) (future work).

**Next:** [Policy](../configuration-guide/policy.md), then [Adapter Instance](../configuration-guide/adapter-instance.md)
