# Deploying with agent based workflow through a playbook

This directory contains a playbook that can be used to deploy an Openshift Cluster using agent based workflow

Code to launch nodes using redfish is included

## Requisites

- valid pull secret
- ansible installed
- bmc urls details of your target nodes

## How to use

1. Prepare a valid inventory file (check the [sample one](inventory.sample) for reference)
2. Run `ansible-playbook -i inventory run.yml`

## Emulating baremetal hosts with kcli

A [kcli plan](kcli_plan.yml) is provided to create 3 vms with specific uuid and  macaddress on a non dhcp libvirt network

The plan can be run with

```
kcli create plan billi
```
