# **Deploying an OpenShift Cluster using BILI workflow**

This document provides a first view at deploying a cluster using bili workflow, which is a subcommand for openshift-install that will generate a custom iso for installing openshift from a set of ZTP-like manifests and in a unattended fashion.

## **Workflow**

### **Requisites**

#### **Packages**

A special openshift-install binary built with agent support must be used. In the future, this will be part of the regular openshift-install binary.

Additionally, NMState needs to be installed and NetworkManager should have a minimum version of 1.30. In the future, this will also be included directly in the agent subcommand.

#### **Cluster manifests**

The input needed for this process is a list of yaml files that use similar content to what is used nowadays for ZTP and that needs to be put in a directory named `cluster-manifests`.

As such, people familiar with this workflow shouldn't have any issues in creating the following files:

- agent-cluster-install.yaml
- cluster-deployment.yaml
- cluster-image-set.yaml
- infraenv.yaml
- nmstateconfig.yaml
- pull-secret.yaml

Alternatively, for people using aicli to interact with AI SAAS API (or on-prem), the following command can be used to generate the needed files from a parameter file:

```
aicli create cluster-manifests --pf bili.yml bili
```

The ability to generate those files on the fly from a valid install config is planned to be added during 4.12 development.

Note that it's mandatory to include a nmstateconfig.yaml file with at least one entry with static ip.

This is used by the installer to locate which node is to be used as *node0*

Nodes also need to get proper fqdns (localhost beeing forbidden), for instance by mean of reverse DNS entries.

### **Deployment**

Once we have created the cluster-manifests, the ISO is generated with the following command:

```
openshift-install agent create image --log-level=debug
```

It is then up to the user to plug the iso to the target nodes.

Additionally, credentials are generated and stored in `auth/kubeconfig`

### **Monitoring progress**

During the process, the assisted service is available in node0 and remains there until this node gets installed.

To monitor progress, we can use API calls, for instance using aicli such as in the following snippet:

```
export AI_URL=192.168.128.11:8090
aicli wait cluster $cluster
```

Note that when node0 gets installed, the service is no longer available and the remainder of the install needs to use typical oc commands (for instance oc get clusterversion).

An `agent wait-for bootstrap-complete/install-complete` is to be added for MVP.

## **Bonus**

When testing, we can use the following kcli commands to create an isolated network and vms for the install using the iso and with specific macs and reverse dns.

```
mv agent.iso /var/lib/libvirt/images
kcli create network -c 192.168.128.0/24 --nodhcp bili
kcli create vm -P iso=agent.iso -P memory=20480 -P numcpus=16 -P disks=[200] -P nets=['{"name":"bili","mac":"de:ad:bb:ef:00:21","ip":"192.168.128.11","reservedns":"true"}'] bili --count=3
```

## **References**

- [early access details](https://source.redhat.com/groups/public/agent/agent_team_blog/internal_early_access_build)
- [demo recording from the dev team](https://drive.google.com/file/d/1cUX0KjaTH1IpBoYeC8lzdfJomCzaHPvh/view?usp=sharing)
- [agent installer branch](https://github.com/openshift/installer/blob/agent-installer)
