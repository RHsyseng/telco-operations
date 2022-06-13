# **Deploying an OpenShift Cluster with disabled nics using Assisted Installer**

This document briefly describes how to run a deployment of an OpenShift Cluster through Assisted Installer when one or several nics need to be disabled.

We will use [Assisted Installer CLI](https://github.com/karmab/aicli) in order to interact with the Assisted Service API in a CLI fashion.

The approach involves using the API to inject a network manager file that will disable the specified nic.

The file needs to be injected both in the discovery iso through an ignition config override and also as an extra cluster manifest so that it applies to the nodes when they get installed.

## **Preparing the network manager file content**

We prepare a file to indicate which nic needs to be disabled (ens4 in our case).

More nics can be specified using a syntax similar to `unmanaged-devices=interface-name:ens4,interface-name:ens5`

```
[main]
rc-manager=file
[connection]
ipv6.dhcp-duid=ll
ipv6.dhcp-iaid=mac
[keyfile]
unmanaged-devices=interface-name:ens4
```

Once the file contains the desired content, we store the corresponding base64 information.

```
BASE64=$(cat $network_file | base64 -w0)
```

In the remainder of this document, replace *BASE64* with the corresponding content.

## **Preparing the manifest file**

We create a directory named manifests where we create two file named `disablenic-master.yaml` and `disablenic-worker.yaml`

```
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  name: disablenic-master
  labels:
    machineconfiguration.openshift.io/role: master
spec:
  config:
    ignition:
      version: 3.1.0
    storage:
      files:
        - contents:
            source: data:text/plain;charset=utf-8;base64,$BASE64
            verification: {}
          filesystem: root
          mode: 420
          path: /etc/NetworkManager/conf.d/disablenic.conf
```

```
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  name: disablenic-worker
  labels:
    machineconfiguration.openshift.io/role: worker
spec:
  config:
    ignition:
      version: 3.1.0
    storage:
      files:
        - contents:
            source: data:text/plain;charset=utf-8;base64,$BASE64
            verification: {}
          filesystem: root
          mode: 420
          path: /etc/NetworkManager/conf.d/disablenic.conf
```

## **Preparing the aicli parameter file**

The parameter file to be used with aicli needs to have both the reference for *ignition\_config\_override* and the information of the directory where the extra manifests are stored.

```
#sno: true
#api_ip: 192.168.122.253
#ingress_ip: 192.168.122.252
#minimal: true
manifests: manifests
ignition_config_override: '{"ignition":{"config":{},"version":"3.1.0"},"storage":{"files":[{"contents":{"source":"data:text/plain;charset=utf-8;base64,$BASE64","verification":{}},"filesystem":"root","mode":420,"overwrite":true,"path":"/etc/NetworkManager/conf.d/disablenic.conf"}]}}'
```

This parameter file can either be used when creating the cluster or when updating it. The corresponding aicli calls would be

```
aicli create cluster $cluster --paramfile $paramfile 
```

or

```
aicli update cluster $cluster --paramfile $paramfile 
```

At this point, one can go through a typical provisioning process with AI, either using aicli or through the UI.
