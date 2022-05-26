# **How to deploy Openshift with Contrail CNI and aicli**

This document provides information on how to deploy Openshift using Contrail CNI and [aicli](https://github.com/karmab/aicli)

It is based on the documentation available publically [here](https://www.juniper.net/documentation/us/en/software/cn-cloud-native22/cn-cloud-native-ocp-install-and-lcm/topics/task/cn-cloud-native-ocp-install-ocp-managed-net.html) but use aicli instead of curl api calls to ease the workflow.

## **Requisites**

* Free nodes to run the install (3 or 1), with 2 nics.
* Valid pull secret with credentials to `hub.juniper.net`
* Aicli installed
* Valid offline token to use with aicli (if using SAAS mode).
* Contrail manifests downloaded from [Juniper Web site](https://www.juniper.net/documentation/us/en/software/cn-cloud-native22/cn-cloud-native-ocp-install-and-lcm/topics/reference/cn-cloud-native-ocp-manifests-and-tools.html) to the directory `contrail-manifests-openshift`.
* Sushy running if planning to use libvirt vms

## **How To proceed**

0. Edit the following files in the downloaded manifests

- `99-network-configmap.yaml`: Specify data network cidr
- `99-disable-offload-master.yaml/99-disable-offload-master-ens4.yaml/99-disable-offload-worker.yaml/99-disable-offload-worker-ens4.yaml`: If deploying on vms, specify the correct nics in all of those files to disable nic offloading.

1. Create a valid parameter file such as [aicli_parameters.yml](aicli_parameters.yml)

Relevant elements for this parameter are the following one:

- `pull_secret`: The path to your pull secret. Defaults to `openshift_pull.json`.
- `network_type`: This is forced to contrail
- `openshift_version`: This currently needs to be 4.8
- `manifests`: the name of the directory where the Contrail manifests have been downloaded
- api_vip and ingress_vip: Mandatory for an HA install
- ignition_config_override: This contains a specific ignition needed for the nodes to properly communicate with Contrail Api server
- `hosts`: This optional section allows the bmc information to be provided so that the discovery iso gets automatically attached and the hosts started automatically. Alternatively, one can download the iso manually and plug it to target nodes.

2. Launch `aicli create deployment --paramfile my_params.yml`
3. Wait around 50mn

## **Reproducing deployment using kcli and aicli**

In this scenario, we will create the following elements:

- create 3 uefi vms with enough memory and cpus and forcing their uuids using a [kcli plan](kcli_plan.yml).
- run the deployment using aicli and the default parameter file.

A makefile is provided for this matter, so simply run `make install` to trigget deployment of all the artifacts
