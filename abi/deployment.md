# **Deploying an OpenShift Cluster using ABI workflow**

This document provides a first view at deploying a cluster using abi workflow, which is a subcommand for openshift-install that will generate a custom iso for installing openshift from an install config in an unattended fashion.

## **Workflow**

### **Requisites**

#### **Packages**

A recent enough openshift-install binary (with agent support) must be used.

Additionally, NMState needs to be installed and NetworkManager should have a minimum version of 1.30. In the future, this will also be included directly in the agent subcommand.

#### **Input manifest**

The input needed for this process is an install config and an agent-config.yaml

### **Deployment**

Once we have created the cluster-manifests, the ISO is generated with the following command:

```
openshift-install agent create image --log-level=debug
```

It is then up to the user to plug the iso to the target nodes.

Additionally, credentials are generated and stored in `auth/kubeconfig`

### **Monitoring progress**

During the process, the assisted service is available in node0 and remains there until this node gets installed.

To monitor progress, we can use the following call:

```
openshift-install agent wait-for bootstrap-complete
```

Note that when node0 gets installed, the service is no longer available and the remainder of the install needs to use typical oc commands (for instance oc get clusterversion).

The following command can also be used to handle this part

```
openshift-install agent wait-for install-complete
```

## **Bonus**

When testing, we can use the following kcli commands to create an isolated network and vms for the install using the iso and with specific macs and reverse dns.

```
mv agent_x86_64.iso /var/lib/libvirt/images
kcli create network -c 192.168.128.0/24 --nodhcp abi
kcli create vm -P iso=agent_x86_64.iso -P memory=20480 -P numcpus=16 -P disks=[200] -P nets=['{"name":"abi","mac":"de:ad:bb:ef:00:21","ip":"192.168.128.11","reservedns":"true"}'] abi --count=3
```

## **References**

- [demo recording from the dev team](https://drive.google.com/file/d/1cUX0KjaTH1IpBoYeC8lzdfJomCzaHPvh/view?usp=sharing)
