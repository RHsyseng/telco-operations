# **A first look at MicroShift**

This document provides information on how to use MicroShift and interact with several instances through ACM.

## **Environment**

* One or several VMs where MicroShift will get deployed
* An OpenShift cluster with ACM installed

## **How To use**

### **Deploying MicroShift**

We will indicate the steps to deploy MicroShift using a RPM version (which has the benefit of allowing to inject extra manifests)

-  We install client tools

```
curl -o oc.tar.gz https://mirror.openshift.com/pub/openshift-v4/clients/oc/latest/linux/oc.tar.gz
tar -xzvf oc.tar.gz
install -t /usr/bin {kubectl,oc}
```

- We install cri-o

```
CRIO_VERSION=1.$(kubectl version -o yaml | grep minor | cut -d: -f2 | sed 's/"//g' | xargs)
OS=$(cat /etc/redhat-release | awk '{print $1"_"$4"_"$2'})
curl -L -o /etc/yum.repos.d/devel:kubic:libcontainers:stable.repo https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/$OS/devel:kubic:libcontainers:stable.repo
curl -L -o /etc/yum.repos.d/devel:kubic:libcontainers:stable:cri-o:$CRIO_VERSION.repo https://download.opensuse.org/repositories/devel:kubic:libcontainers:stable:cri-o:$CRIO_VERSION/$OS/devel:kubic:libcontainers:stable:cri-o:$CRIO_VERSION.repo
dnf -y install cri-o conntrack cri-tools
sed -i 's@conmon = .*@conmon = "/bin/conmon"@' /etc/crio/crio.conf
systemctl enable --now crio
```

- We install and launch MicroShift

```
dnf copr enable -y @redhat-et/microshift
dnf install -y microshift firewalld
systemctl enable microshift --now
```

After a little while, MicroShift will be up and running, and kubeconfig can be found at `/var/lib/microshift/resources/kubeadmin/kubeconfig`

### **Deploying with podman**

To deploy using podman, we replace step 3 with the following commands:

```
curl -o /etc/systemd/system/microshift.service https://raw.githubusercontent.com/redhat-et/microshift/main/packaging/systemd/microshift-containerized.service
systemctl enable microshift --now
KUBEADMINDIR=/var/lib/microshift/resources/kubeadmin
mkdir -p $KUBEADMINDIR
while true ; do podman cp microshift:$KUBEADMINDIR/kubeconfig $KUBEADMINDIR && break ; sleep 5 ; done
```

### **Registering with an ACM cluster**

The script [acm.sh](acm.sh) can be used for this purpose. Note that proper DNS is needed for both the MicroShift Instance and target ACM cluster.

[This video](https://drive.google.com/file/d/1QdbGzW4IRSwFLIIuov7_yrHp0TqPPptu/view) shows generic workflow along with ACM integration

## **Bonus: deploying with a kcli plan*

The repo [kcli-plan-microshift](https://github.com/karmab/kcli-plan-microshift) automates the deployment of MicroShift for any number of vms.

The plan supports most of the features documented in MicroShift documentation:

- installation through podman or through rpm
- injection of extra manifests
- registration to ACM instance
