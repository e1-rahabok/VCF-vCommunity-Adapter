# Policy: Activate the Required Metrics

Some metrics and properties this pack needs are **deactivated by default** in VCF Operations. Without them, the features below have no data. Activate them in the policy that applies to your ESXi hosts. The steps use the Default Policy.

| Feature without data | To activate (Host System, **Network**) | State | Instanced State |
| :--- | :--- | :--- | :--- |
| Bad Network Packets (in Cluster Performance and ESXi Performance) | **Total Packets Received** (`net|packetsRx_summation_sum`) | Activated | Optional |
| | **Total Packets Transmitted** (`net|packetsTx_summation_sum`) | Activated | Optional |
| [Network Speed Degradation](../reference/metrics/network-speed-degradation.md) | **Configured Speed** (`net|configuredSpeed`), a property | Activated | **Activated**: one value per physical NIC is needed |

1. Go to **Administration** > **Configurations** > **Policy Definition**.
2. Edit the **Default Policy**, and open **Metrics and Properties**.
3. Set **Select Object Type** to **Host System**.
4. Expand **Network**.
5. Set the states as in the table above.
   - **Configured Speed** is listed with the properties of **Network**. Its tooltip reads: *"The configured network speed of the network card. If this is higher than actual, the card is not operating at its full capacity."*
   - Next to it, **Actual Speed** (`net|speed`) is activated by default. Leave it on.
6. Check that these four are also **Activated**. They are by default.
   - **Total Received Packets Dropped** (`net|droppedRx_summation_sum`)
   - **Total Transmitted Packets Dropped** (`net|droppedTx_summation_sum`)
   - **Total Error Packets Received** (`net|errorsRx_summation_sum`)
   - **Total Error Packets Transmitted** (`net|errorsTx_summation_sum`)
7. Save the policy.

![Default Policy, Host System, Network: Total Packets Received and Total Packets Transmitted activated](images/policy-host-network-packets.png)

The metrics have data from the next collection cycle.

> **To verify on a live system:** once Configured Speed is active, `net:vmnic0|configuredSpeed` should appear as a property on the host, next to `net:vmnic0|speed`. Its value for a NIC set to auto-negotiate is not yet known.

---

**Next:** [Create an Adapter Instance](adapter-instance.md)
