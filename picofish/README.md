# Picofish

> **WARNING**: The work exposed here is not supported in any way by Red Hat, this is the result of exploratory work. Use at your own risk.

`picofish` is a flask based proxy that intercepts redfish API requests and modifies the ones required to use virtual media in Supermicro hardware required to deploy OpenShift IPI on bare metal, while leaving the ones not required unmodified.

This directory contains the [Containerfile](./Containerfile) and [source code](./picofish.py) for the `picofish` tool. 

## Usage

It requires the following environment variables:

* `HOST` - The IP/hostname of the 'real' Supermicro BMC
* `USERNAME/PASSWORD` - The username and password of the 'real' Supermicro BMC

```
podman run -p 9000:9000 -e HOST=10.19.110.8 -e USERNAME=ADMIN -e PASSWORD=ADMIN quay.io/rhsysdeseng/picofish:latest
sudo firewall-cmd --add-port=9000/tcp
```

Then, in the `install-config.yaml` file, it is required to specify the IP where the container is running instead of the 'real' BMC:

```
bmcAddress: redfish-virtualmedia://10.19.110.17:9000/redfish/v1/Systems/1
```

> **NOTE**: Every container is mapped to a single BMC, but if more hosts are required, different ports can be used (9001, 9002,...)