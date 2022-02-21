# **Running HyperShift + Kubevirt**

This document explains how to deploy HyperShift in OpenShift and then use Kubevirt to deploy worker nodes for our `HostedClusters`.

## **Requirements**

* OpenShift Cluster acting as Hub (We tested with 4.9.12)
* HyperShift (commit [8859e19]( https://github.com/openshift/hypershift/commit/8859e19e07f8eaa98cd316b9adb138d9e6a7d928))
* CNV 4.9.2 (CSV: `kubevirt-hyperconverged-operator.v4.9.2`)

## **Deploying CNV**

Just deploy CNV from the Operator Marketplace and create a default `Hyperconverged` object.

## **Deploying HyperShift**

At this point, we need to build HyperShift in order to get it deployed, HyperShift requires Go 1.17. We will install Go 1.17 and then build and deploy HyperShift.

1. Download and Install Go 1.17:

    ~~~sh
    wget https://go.dev/dl/go1.17.6.linux-amd64.tar.gz
    rm -rf /usr/local/go && tar -C /usr/local -xzf go1.17.6.linux-amd64.tar.gz
    ~~~

2. Add `/usr/local/go/bin` to your PATH env var.
3. Clone HyperShift repo:

    ~~~sh
    git clone https://github.com/openshift/hypershift.git
    ~~~

4. Build HyperShift:

    ~~~sh
    cd hypershift
    make build
    ~~~

5. Deploy HyperShift:

    ~~~sh
    ./bin/hypershift install
    ~~~

6. Wait for the HyperShift operator to be running:

    ~~~sh
    oc -n hypershift get pod
    ~~~

7. Create a `HostedCluster` with the HyperShift cli:

    > **NOTE**: A `HostedCluster` is how we refer to a containerized control plane. A node pool specifies the number of workers (2 in this case) that will be created in the provider (Kubevirt in this case).

    ~~~sh
    ./bin/hypershift create cluster kubevirt --name diplodocus --pull-secret /root/ericsson-upi/pull-secret.json --ssh-key /root/.ssh/id_rsa.pub --node-pool-replicas 2 --containerdisk quay.io/containerdisks/rhcos:4.9
    ~~~

8. Once the `HostedCluster` is up and running you can export the kubeconfig:

    ~~~sh
    ./bin/hypershift create kubeconfig > kubeconfig
    ~~~

9. We can also destroy the `HostedCluster`:

    ~~~sh
    ./bin/hypershift destroy cluster kubevirt --name diplodocus
    ~~~

## **Some technical details**

* The access to the `HostedCluster` API is exposed via a NodePort in the cluster running HyperShift.
* Some things will not work: Access to the OCP Web Console, commands like "oc rsh/oc debug" in the `HostedCluster`.
* We can get the ignition used for the provisioning of worker nodes as follows:

    ~~~sh
    export CLUSTER=diplodocus
    curl -k -H "Authorization: Bearer $(oc -n clusters-${CLUSTER} get secret $(oc -n clusters-${CLUSTER} get secret | grep token-${CLUSTER}  | awk '{print $1}') -o jsonpath={.data.token})" https://$(oc get node -o wide | grep master | head -1 | awk '{print $6}'):$(oc -n clusters-${CLUSTER} get svc ignition-server -o jsonpath={.spec.ports[0].nodePort})/ignition
    ~~~
