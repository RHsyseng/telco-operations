# **Running SNO with extra workers**

This document provides information on how to deploy a SNO and add extra workers to it, and then study behaviour when losing some of the workers or the initial node.

Note: appendix contains kcli commands used to speed up the workflow.

## **Environment**

* We run all the deployments using libvirt VMs, although the procedure would be the same for baremetal nodes.

## **Initial deployment**

### Deploying SNO

We leverage bootstrap in place procedure to generate a valid ignition file that is then embedded using coreos-installer.

We start with the following install config where:

- we specify platform as `None`
- we indicate in the bootstrap in place the disk to use for installation
- we set network type to `OVNKubernetes`


The `install-config.yaml` file looks like:

```
apiVersion: v1
baseDomain: karmalabs.com
compute:
- name: worker
  replicas: 0
controlPlane:
  name: master
  replicas: 1
metadata:
  name: mycluster
networking:
  networkType: OVNKubernetes
  machineNetwork:
  - cidr: 10.0.0.0/16
  clusterNetwork:
  - cidr: 10.132.0.0/14
    hostPrefix: 23
  serviceNetwork:
  - 172.30.0.0/16
platform:
  none: {}
BootstrapInPlace:
  InstallationDisk: /dev/vda
pullSecret: 'XXX'
sshKey: |
  ssh-rsa ZZZ
```

With this install config, we then generate an ignition to use for SNO:

```
mkdir -p ocp
cp install-config.yaml ocp
openshift-install --dir=ocp create single-node-ignition-config
```

This will generate a file named `bootstrap-in-place-for-live-iso.ign` that we can embed into any valid rhcos live iso, such as the [latest one](https://mirror.openshift.com/pub/openshift-v4/x86_64/dependencies/rhcos/latest/rhcos-live.x86_64.iso) using the following invocation:

```
coreos-installer iso ignition embed -fi iso.ign bootstrap-in-place-for-live-iso.ign -o bip.iso rhcos-live.x86_64.iso
```

Once we boot a given node with this generated `bip.iso`, after a while, we should see an output similar to the following one:

```
oc get nodes
NAME                          STATUS   ROLES           AGE     VERSION
mycluster-sno.karmalabs.com   Ready    master,worker   176m    v1.22.3+b93fd35
```

### Adding additional workers

Although ignition for workers is not generated when running openshift-install as in the previous section, this can be retrieved using curl:

`curl ${NODE_IP}:22624/config/worker > worker.ign`

To add more workers to the SNO, we craft an openshift iso using coreos-installer and making sure it installs the following target ignition:

```
{
    "ignition": {
        "config": {
           "merge": [
              {
              "source": "http://192.168.122.235:22624/config/worker"
              }
           ]
        },
    "version": "3.1.0"
    },
    "storage": {
        "files": [
            {
                "contents": {
                    "source": "data:text/plain;charset=utf-8;base64,MTI3LjAuMC4xICAgbG9jYWxob3N0IGxvY2FsaG9zdC5sb2NhbGRvbWFpbiBsb2NhbGhvc3Q0IGxvY2FsaG9zdDQubG9jYWxkb21haW40Cjo6MSAgICAgICAgIGxvY2FsaG9zdCBsb2NhbGhvc3QubG9jYWxkb21haW4gbG9jYWxob3N0NiBsb2NhbGhvc3Q2LmxvY2FsZG9tYWluNgoxOTIuMTY4LjEyMi4yMzUgYXBpLWludC5teWNsdXN0ZXIua2FybWFsYWJzLmNvbSBhcGkubXljbHVzdGVyLmthcm1hbGFicy5jb20=",
                    "verification": {}
                },
                "filesystem": "root",
                "mode": 420,
                "overwrite": true,
                "path": "/etc/hosts"
            }
        ]
    }
}
```

This ignition file contains the following elements:

- the source pointing to the final ignition to use
- an overwrite of `/etc/hosts` so that api.$cluster.$domain and api-int.$cluster.$domain point to the ip of the SNO

```
127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
::1         localhost localhost.localdomain localhost6 localhost6.localdomain6
192.168.122.235 api-int.mycluster.karmalabs.com api.mycluster.karmalabs.com
```

Provided this content got copied to `/root/config.ign` and we booted from rhcos live iso, we write it to disk using the following invocation from the live booted system:

```
coreos-installer install --ignition=/root/config.ign /dev/vda
```

Note that this is a two step process, we can't embed this ignition directly in the iso, since we need to persist it.

Once booted, the nodes will issue a CSR that needs to be be signed in order for them to join the cluster

```
oc get csr -o go-template='{{range .items}}{{if not .status}}{{.metadata.name}}{{"\n"}}{{end}}{{end}}' | xargs oc adm certificate approve
```

After a while, we should see an output similar to the following one:


```
oc get nodes

NAME                          STATUS   ROLES           AGE     VERSION
mycluster-sno.karmalabs.com   Ready    master,worker   176m    v1.22.3+b93fd35
mycluster-worker-0            Ready    worker          4m41s   v1.22.3+b93fd35
mycluster-worker-1            Ready    worker          4m38s   v1.22.3+b93fd35
```

## **Testing**

### Ingress controller behaviour

If we check the ingress controller by using `oc get ingresscontroller default -n openshift-ingress-operator -o yaml`, we can adjust its node placement pointing to the master role, to guarantee that the router pod will only ever run on the SNO:

```
  nodePlacement:
    nodeSelector:
      matchLabels:
        node-role.kubernetes.io/master: ""
```

A full [ingress yaml](99-ingress-controller.yaml) can be provided as extra manifest at install time.

This could be patched to run on the workers instead, but we would need to implement manually a virtual IP mechanism along with keepalived static pods for the ingress to run properly there. We provide such assets [here](keepalived)

### Testing with a sample app

We use a dummy app based on a daemonset and targeting the worker nodes, that we label accordingly:

```
oc label node $worker1 node-role.kubernetes.io/no-sno=""
oc label node $worker2 node-role.kubernetes.io/no-sno=""
oc create -f sampleapp.yaml
```

Once the ds was running, we validated access to the app by using `curl $WORKER_IP:$NODE_PORT` and were granted by a `Hello, Openshift` message.
We also validated access using the exposed route.
We then stopped the control plane and confirmed the app was still available through nodeport.
Service wouldn't be accessible through a route at this point wouldn't be accessible since it's running on the control plane

## **Deploying using kcli**

```
OCP: 4.10
Version used: c5c9c8863cc9d0b45196c9b2a7166b553b5962cb
```

### SNO

We use `kcli create cluster openshift` with the following `kcli_parameters.yml` file:

```
version: stable
tag: 4.10
cluster: mycluster
sno: true
sno_virtual: true
network_type: OVNKubernetes
domain: karmalabs.com
memory: 32768
numcpus: 16
disk_size: 100
network: default
```

### Extra workers

We generate an iso embedding a target ignition pointing to the sno api (and targetting primary disk):

```
kcli create openshift-iso mycluster.karmalabs.com
```

Note that the iso could be used instead directly on a physical node.

We can then create any number of  (virtual) workers with the following invocation where we create a libvirt dhcp reservation to force hostnames:

```
kcli create vm -P iso=mycluster.iso -P disks=[30] -P memory=20480 -P numcpus=16 -P nets=['{"name": "default", "reserveip": "true", "ip": "192.168.122.200"}']  -P domain=karmalabs.com mycluster-worker --count 2
```
