# **OCP Bare Metal compact cluster using VMs with kcli**

We will leverage [`kcli`](https://kcli.readthedocs.io/) to create our virtual environment as if it was a baremetal one.

The `kcli` baremetal plan creates an _installer_ VM with all the required software, configuration and automation required, including for example [sushy-tools](https://github.com/openstack/sushy-tools) to expose a RedFish API for the VMs so they can be treated as baremetal hosts.

## **OCP cluster architecture**

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│ ┌──────────────────────────────────┐  ┌───────────────────────────────┐  │
│ │                                  │  │                               │  │
│ │    ┌────────────────────┐        │  │                               │  │
│ │    │ hypershift cluster │◄───────┼──┼────────┬───┐                  │  │
│ │    └────────────────────┘        │  │        │   │                  │  │
│ │                                  │  │        │   │                  │  │
│ │                                  │  │        │   │                  │  │
│ │           ┌──────────────┐       │  │        │   │                  │  │
│ │           │    master-2  │       │  │        │   │                  │  │
│ │        ┌──┴───────────┐  │       │  │        │ ┌─┴────────────┐     │  │
│ │        │    master-1  │  │       │  │        │ │   worker-1   │     │  │
│ │    ┌───┴──────────┐   │  │       │  │      ┌─┴─┴──────────┐   │     │  │
│ │    │    master-0  │   │  │       │  │      │    worker-0  │   │     │  │
│ │    │              │   │  │       │  │      │              │   │     │  │
│ │    │              │   │  │       │  │      │              │   │     │  │
│ │    │              │   ├─┬┘       │  │      │              │   │     │  │
│ │    │              │   │ │        │  │      │              │   │     │  │
│ │    │ "real" OCP   ├─┬─┘ │        │  │      │              ├─┬─┘     │  │
│ │    │              │ │   │        │  │      │              │ │       │  │
│ │    └────────────┬─┘ │   │        │  │      └────────────┬─┘ │       │  │
│ │                 │   │   │        │  │                   │   │       │  │
│ │                 │   │   │        │  │                   │   │       │  │
│ │                 │   │   │        │  │                   │   │       │  │
│ │ ────────────────┴───┴───┴──────┐ │  │ ┌─────────────────┴───┴─────  │  │
│ │        libvirt-net-1           │ │  │ │      libvirt-net-2          │  │
│ └────────────────────────────────┼─┘  └─┼─────────────────────────────┘  │
│                                  │      │                                │
│                                ┌─┴──────┴─┐                              │
│                                │          │                              │
│                                │   eth0   │     Hypervisor               │
│                                │          │                              │
└────────────────────────────────┴──────────┴──────────────────────────────┘
```

Instead of using real networks, we will use libvirt networks for simplicity and to reduce the number of external requisites.

## **Versions used**

* OCP compact cluster (3 masters) version 4.9.21 (IPI baremetal)
* Local Storage Operator 4.9.0-202202120107

## **Requisites**

* Copy/download the pull-secret.json

* Define a few variables:

~~~sh
export CLUSTER="ocp"
export OCPCLUSTER_NETWORK_CIDR="192.168.124.0/24"
export OCPCLUSTER_NETWORK_DOMAIN="krnl.es"
export OCPCLUSTER_NETWORK_NAME="krnl"
export HOSTEDCLUSTER_NETWORK_CIDR="192.168.125.0/24"
export HOSTEDCLUSTER_NETWORK_DOMAIN="hosted0.krnl.es"
export HOSTEDCLUSTER_NETWORK_NAME="hosted0-krnl"
export API="api.${CLUSTER}.${OCPCLUSTER_NETWORK_DOMAIN}"
export API_IP="192.168.124.101"
export INGRESS_IP="192.168.124.102"
~~~

* Setup external DNS as required. Ensure those are *ok* with no `/etc/hosts` tricks... otherwise things can go south. In this example:

~~~sh
api.ocp.krnl.es.    A	192.168.124.101
*.apps.ocp.krnl.es. A	192.168.124.102
# Those three entires correspond to the IPs of the 3 master hosts
api.hosted0.krnl.es A 192.168.124.10
api.hosted0.krnl.es A 192.168.124.11
api.hosted0.krnl.es A 192.168.124.12
~~~

* Create the libvirt netwoks:

~~~sh
kcli create network -c ${OCPCLUSTER_NETWORK_CIDR} --domain ${OCPCLUSTER_NETWORK_DOMAIN} ${OCPCLUSTER_NETWORK_NAME}
kcli create network -c ${HOSTEDCLUSTER_NETWORK_CIDR} --domain ${HOSTEDCLUSTER_NETWORK_DOMAIN} ${HOSTEDCLUSTER_NETWORK_NAME}
~~~

To check it:

~~~sh
sudo virsh net-list

Name           State    Autostart   Persistent
-------------------------------------------------
default        active   yes         yes
hosted0-krnl   active   yes         yes
krnl           active   yes         yes
~~~

* Allow traffic from each other:

~~~sh
sudo iptables -I FORWARD 1 -j ACCEPT \
  -i ${OCPCLUSTER_NETWORK_NAME} -o ${HOSTEDCLUSTER_NETWORK_NAME} \
  -s ${OCPCLUSTER_NETWORK_CIDR} -d ${HOSTEDCLUSTER_NETWORK_CIDR}
sudo iptables -I FORWARD 2 -j ACCEPT \
  -i ${HOSTEDCLUSTER_NETWORK_NAME} -o ${OCPCLUSTER_NETWORK_NAME} \
  -s ${HOSTEDCLUSTER_NETWORK_CIDR} -d ${OCPCLUSTER_NETWORK_CIDR}
~~~

* Reserve the MAC/IP pair and set a hostname for the masters

The masters will get known MAC addresses (`aa:aa:aa:aa:aa:0[1,2,3]`) by default, so we will leverage this to create static reservations and DNS entries in the libvirt network as per [this blog article](https://lukas.zapletalovi.com/2020/01/aaaa-dns-record-in-libvirt.html)

For the OCP network (krnl in this example):

~~~xml
<ip family="ipv4" address="192.168.124.1" prefix="24">
  <dhcp>
    <range start="192.168.124.100" end="192.168.124.254"/>
    <host mac="aa:aa:aa:aa:aa:01" name="ocp-master-0.krnl.es" ip="192.168.124.10"/>
    <host mac="aa:aa:aa:aa:aa:02" name="ocp-master-1.krnl.es" ip="192.168.124.11"/>
    <host mac="aa:aa:aa:aa:aa:03" name="ocp-master-2.krnl.es" ip="192.168.124.12"/>
  </dhcp>
</ip>
~~~

For the hosted cluster network (hosted0-krnl in this example) we will create the workers using `kcli create vm` and setting the parameters as we want (for example, the MAC address to be `aa:bb:cc:dd:ee:ff`):

~~~xml
<ip family="ipv4" address="192.168.125.1" prefix="24">
  <dhcp>
    <range start="192.168.125.100" end="192.168.125.254"/>
    <host mac="aa:bb:cc:dd:ee:ff" name="ocp-worker-0.hosted0.krnl.es" ip="192.168.125.10"/>
    <host mac="aa:bb:cc:dd:ee:fa" name="ocp-worker-1.hosted0.krnl.es" ip="192.168.125.11"/>
  </dhcp>
</ip>
~~~

In order to do this, `virsh net-edit <network>` will open the $EDITOR to perform the changes, then `virsh net-destroy <network> && virsh net-start <network>` will apply those changes.

> **NOTE**: `virsh net-destroy` won't destroy the network, it only stops it.

## **Install the cluster**

* Clone the baremetal plan repository:

~~~sh
git clone https://github.com/karmab/kcli-openshift4-baremetal.git
cd kcli-openshift4-baremetal
~~~

* Create the parameters file

~~~sh
envsubst <<"EOF" > ocp.yml
version: stable
tag: "4.9"
cluster: ocp
domain: ${OCPCLUSTER_NETWORK_DOMAIN}
provisioning_enable: false
ztp_spoke_deploy: false
virtual_masters: true
virtual_masters_memory: 32768
virtual_masters_baremetal_mac_prefix: aa:aa:aa:aa:aa
launch_steps: true
deploy_openshift: true
baremetal_cidr: ${OCPCLUSTER_NETWORK_CIDR}
baremetal_net: ${OCPCLUSTER_NETWORK_NAME}
api_ip: ${API_IP}
ingress_ip: ${INGRESS_IP}
pullsecret: pull-secret.json
installer_numcpus: 4
installer_memory: 4096
EOF
~~~

* Run the installation:

~~~sh
kcli create plan ocp --pf ocp.yml
~~~

We want to use some persistent volumes so we will deploy the Local Storage Operator and configure it to use a couple of disks on each master.

* Add more disks to the masters:

~~~sh
kcli update vm ocp-master-0 -P disks=[30,10,10]
kcli update vm ocp-master-1 -P disks=[30,10,10]
kcli update vm ocp-master-2 -P disks=[30,10,10]
~~~

The installation progress can be followed as:

~~~sh
kcli console -s ocp-installer
~~~

While the installation finishes (it takes a while), a couple of empty VMs to be used as workers can be created:

~~~sh
kcli create vm -P machine=pc-q35-rhel8.2.0 -P disks=['{"diskname":"sda","size":"120","interface": "scsi"}'] -P uuid=11111111-1111-1111-1111-111111111111 -P start=false -P nets=['{"name":"hosted0-krnl","mac":"aa:bb:cc:dd:ee:ff"}'] -P numcpus=8 -P memory=8192 ocp-worker-0
kcli create vm -P machine=pc-q35-rhel8.2.0 -P disks=['{"diskname":"sda","size":"120","interface": "scsi"}'] -P uuid=11111111-1111-1111-1111-111111111112 -P start=false -P nets=['{"name":"hosted0-krnl","mac":"aa:bb:cc:dd:ee:fa"}'] -P numcpus=8 -P memory=8192 ocp-worker-1
~~~

## **Verify the installation**

Once finished, you can jump into the _installer_ VM where the KUBECONFIG variable is already set (as root):

~~~sh
kcli ssh ocp-installer

sudo -i
oc get clusterversion
~~~

## **Local storage Operator**

* Create the namespace

~~~sh
oc create namespace openshift-local-storage
oc annotate project openshift-local-storage openshift.io/node-selector=''
~~~

* Create the `OperatorGroup` and `Subscription`:

~~~sh
export OC_VERSION=$(oc version -o yaml | grep openshiftVersion | grep -o '[0-9]*[.][0-9]*' | head -1)

envsubst <<"EOF" | oc apply -f -
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: local-operator-group
  namespace: openshift-local-storage
spec:
  targetNamespaces:
    - openshift-local-storage
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: local-storage-operator
  namespace: openshift-local-storage
spec:
  channel: "${OC_VERSION}"
  installPlanApproval: Automatic 
  name: local-storage-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF
~~~

> **NOTE**: Those steps can be performed easily using [`tasty`](https://github.com/karmab/tasty) as `tasty install local-storage-operator`. Yummy!

* Wait for the operator to be fully deployed and the CRDs created:

~~~sh
until oc wait crd/localvolumes.local.storage.openshift.io --for condition=established --timeout 10s >/dev/null 2>&1 ; do sleep 1 ; done
~~~

* Create the `LocalVolume` object that will use the `/dev/vd[a,b]` devices as PV on the 3 masters:

~~~sh
cat <<EOF| oc apply -f -
apiVersion: "local.storage.openshift.io/v1"
kind: "LocalVolume"
metadata:
  name: "local-disks"
  namespace: "openshift-local-storage" 
spec:
  tolerations:
    - key: node-role.kubernetes.io/master
      operator: Exists
  nodeSelector: 
    nodeSelectorTerms:
    - matchExpressions:
        - key: node-role.kubernetes.io/master
          operator: Exists
  storageClassDevices:
    - storageClassName: "local-sc" 
      volumeMode: Filesystem 
      fsType: xfs 
      devicePaths: 
        - /dev/vda
        - /dev/vdb
EOF
~~~

* Wait for the `StorageClass` to be created and set it as default:

~~~sh
until oc get sc/local-sc >/dev/null 2>&1 ; do sleep 1 ; done
oc patch storageclass local-sc -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
~~~
