# **Deploying a BGP service using metallb**

This document describes how to consume BGP in metallb to expose a service through this protocol.

## **Workflow**

### **Requisites**

- An openshift cluster with a valid storage cluster and metallb operator deployed
- A vm or a dedicated Baremetal to be used as BGP node (This could be a dedicated router too).
- Some unused ips

### **Deployment**

#### BGP box

First, we edit `frr/frr.conf` and specify the ip of the BGP node and those of the OpenShift nodes.
 
We run BGP stack through podman

```
podman run -d --rm  -v /root/frr:/etc/frr:Z --net=host --name frr-upstream --privileged quay.io/frrouting/frr:8.5.0
```

#### OpenShift environment

We deploy metallb and configure it for BGP.

We need to edit

- `01_pool.yml` to specify which ips to use with BGP. Note that those ips need to available and not belong to the network segment used by the Openshift installation.
- `03_peers.yml` first and indicate the ip of the BGP node (BGP_IP)

```
oc create -f 01_pool.yml
oc create -f 02_bfd.yml
oc create -f 03_peers.yml
oc create -f 03_advertisements.yml
```

We can check from one of the speaker nodes how it sees the BGP node as neighbor

```
oc -n openshift-operators exec -it speaker-275d5  -c frr -- vtysh -c "show ip bgp neighbor"
```

We can see the same from the BGP node

```
podman exec -it frr-upstream vtysh -c "show bgp neighbors"
```

### **Consuming service**

At this point, we can create a deployment and an associated service (with an annotation to use our BGP pool).

```
oc create -f hello_deployment.yml
```

By doing a describe of the service, we will see

- which IP it got assigned
- how the service is beeing advertised on the different nodes

We can check from one of the speaker nodes how the ip of the service is beeing advertised

```
oc -n openshift-operators exec -it speaker-275d5  -c frr -- vtysh -c "show bgp ipv4"
```

We can see the same from the BGP node

```
podman exec -it frr-upstream   vtysh -c "show ip route"
```

## **Bonus**

When testing, we can use the following kcli commands to create a cluster with metallb and a dedicated vm with frr running as container

```
kcli create vm -i centos8stream -P memory=8192 -P numcpus=16 -P cmds=['yum -y install podman'] bgp-node
kcli create cluster  openshift -P clusterprofile=sample-openshift-compact myopenshift --force
BGP_IP=$(kcli info vm bgp-node -fv ip)
kcli create app openshift metallb-operator -P bgp=true -P metallb_peer_address=$BGP_IP
```

## **References**

- [https://cloud.redhat.com/blog/metallb-in-bgp-mode](https://cloud.redhat.com/blog/metallb-in-bgp-mode)
- [https://cloud.redhat.com/blog/advanced-metallb-configuration](https://cloud.redhat.com/blog/advanced-metallb-configuration)
