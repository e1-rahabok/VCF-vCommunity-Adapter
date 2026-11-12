# Dark Site Installation

Use these steps when the Cloud Proxies cannot reach `ghcr.io`. You copy the pack's container image into a private registry, and point VCF Operations at that registry. If the Cloud Proxy can reach `ghcr.io`, you don't need this page: it pulls the image itself, see [How It Works](how-it-works.md).

**On this page:**

- [How the Cloud Proxy finds the image](#how-the-cloud-proxy-finds-the-image)
- [Step 1–4: On the Local Machine](#step-14-on-the-local-machine)
- [Step 5: On Each VCF Operations Cluster Node](#step-5-on-each-vcf-operations-cluster-node-excluding-cloud-proxies)
- [Step 6: On Each Cloud Proxy](#step-6-on-each-cloud-proxy)

---

## How the Cloud Proxy finds the image

The Cloud Proxy pulls the image named in `vCommunity.conf`, a file inside the `.pak` file. It combines three fields and pulls by digest, not by tag:

| Field | Value |
| :--- | :--- |
| `REGISTRY` | `ghcr.io` |
| `REPOSITORY` | `/e1-rahabok/vcf-operations-vcommunity` |
| `DIGEST` | `sha256:<digest>`, different for each version of the pack |

To find the digest for your version, read `vCommunity.conf` on a VCF Operations node after the install. The path is in Step 5.

In your private registry, keep the same repository path and the same digest. Only the registry changes, in Step 5.

## Step 1–4: On the Local Machine

**Step 1: Find the image tag for your version.**

The images are listed on GitHub:

```
https://github.com/users/e1-rahabok/packages/container/package/vcf-operations-vcommunity
```

Tags have the form `<version>_<build time>`, for example `0.8.1_<build time>`. Use the tag whose digest matches `DIGEST` in your `vCommunity.conf`. In the commands below, replace `<tag>` with it.

**Step 2: Pull the image to your local machine.**

```bash
docker pull ghcr.io/e1-rahabok/vcf-operations-vcommunity:<tag>
```

**Step 3: Tag the image for your private registry.**

Replace `private-registry.local.network` with the FQDN of your registry in every command. Keep the path `e1-rahabok/vcf-operations-vcommunity`, because it must match `REPOSITORY`.

```bash
docker tag ghcr.io/e1-rahabok/vcf-operations-vcommunity:<tag> private-registry.local.network/e1-rahabok/vcf-operations-vcommunity:<tag>
```

**Step 4: Push the image to your private registry.**

```bash
docker push private-registry.local.network/e1-rahabok/vcf-operations-vcommunity:<tag>
```

`docker push` prints a digest at the end. It must equal `DIGEST`, or the Cloud Proxy cannot find the image. If it differs, copy the image with a tool that keeps the digest, such as `skopeo copy` or `crane copy`.

---

## Step 5: On Each VCF Operations Cluster Node (excluding Cloud Proxies)

On every node, set the `REGISTRY` field in:

```
$VCOPS_BASE/user/plugins/inbound/vCommunity.conf
```

```
REGISTRY=private-registry.local.network
```

---

## Step 6: On Each Cloud Proxy

Restart the collector so it reads the new registry:

```bash
service collector restart
```

---

Then create the Adapter Instances as usual, see [Adapter Instance](../configuration-guide/adapter-instance.md). The Cloud Proxy pulls the image from your private registry.

Each version of the pack has its own digest. After an upgrade, repeat steps 1 to 4 for the new image, and check that `REGISTRY` in `vCommunity.conf` still points to your registry.

---

**Next:** [Policy](../configuration-guide/policy.md), then [Adapter Instance](../configuration-guide/adapter-instance.md).
