# **HyperShift + Bare Metal workers using 'agent' provider**

This document explains how to deploy HyperShift in OpenShift and then use the 'agent' provider to deploy bare metal worker nodes for our `HostedClusters`.

This work tries to answer the questions exposed in [this card](https://issues.redhat.com/browse/KNIECO-4458).

> **WARNING**: HyperShift is a work-in-progress project, and it is not officially fully supported by Red Hat.

## **Hypershift Operator requirements**

* cluster-admin access to an OpenShift Cluster to deploy the CRDs + operator. See the [ocp-bm-cluster](../assets/ocp-bm-cluster.md) document on how to deploy a baremetal OCP cluster using kcli with virtual masters.
* 1 filesystem type Persistent Volume (4Gi minimum) to store the `etcd` database for demo purposes (3x for 'production' environments).
* Multicluster Engine deployed, we installed it through RHACM 2.5.

## **Versions used**

* OCP compact cluster (3 masters) version 4.11-rc1 (IPI baremetal)
* Local Storage Operator 4.10.0-202206291026
* RHACM 2.5
* HyperShift Operator 4.11 image

## **Deploying HyperShift**

HyperShift is deployed using the HyperShift binary, we can get this binary from the `hypershift-operator` image:

~~~sh
podman cp $(podman create --name hypershift --rm quay.io/hypershift/hypershift-operator:4.11):/usr/bin/hypershift /tmp/hypershift && podman rm -f hypershift
sudo install -m 0755 -o root -g root /tmp/hypershift /usr/local/bin/hypershift
~~~

Now that we have the binary installed in our system, we can go ahead and deploy the HyperShift operator in our cluster.

~~~sh
hypershift install render --hypershift-image quay.io/hypershift/hypershift-operator:4.11 | oc apply -f -
~~~

> **NOTE**: There are a few more flags to customize the HyperShift operator installation but they are out of the scope of this document.

Using `hypershift install --render` will output a yaml file with all the assets required to deploy HyperShift. Such output has been [included in the assets folder](../assets/hypershift-install.yaml) as a reference.

We should have an HyperShift pod running in the `hypershift` namespace:

~~~sh
oc -n hypershift get pods

NAME                        READY   STATUS    RESTARTS   AGE
operator-56c64d7bb5-sld8j   1/1     Running   0          54s
~~~



## **Deploy a hosted cluster**

There are two main CRDs to describe a hosted cluster:

* [`HostedCluster`](https://hypershift-docs.netlify.app/reference/api/#hypershift.openshift.io/v1alpha1.HostedCluster) defines the control plane hosted in the management OpenShift
* [`NodePool`](https://hypershift-docs.netlify.app/reference/api/#hypershift.openshift.io/v1alpha1.NodePool) defines the nodes that will be created/attached to a hosted cluster

The `hostedcluster.spec.platform` specifies the underlying infrastructure provider for the cluster and is used to configure platform specific behavior, so depending on the environment it is required to configure it properly.

In this document we will cover the 'agent' provider.

### **Prerequisites**

#### **DNS**

Proper DNS records for the API and Ingress endpoints are required for the installation to fully succeed. There is a limitation that prevents us from being able to specify a VIP for the Ingress, so depending on the number of workers we plan to add to a cluster we may need to update the ingress wildcard record for the installation to succeed. More info [here](https://bugzilla.redhat.com/show_bug.cgi?id=2105983).

> :information_source: API record should point to the IPs of the nodes in the cluster where the API pods run (API gets exposed as a NodePort). Ingress wildcard record should point to the IP of the worker running the router.

~~~sh
api.hypercluster1.e2e.bos.redhat.com.    IN A 10.19.3.23
api.hypercluster1.e2e.bos.redhat.com.    IN A 10.19.3.24
api.hypercluster1.e2e.bos.redhat.com.    IN A 10.19.3.25
*.apps.hypercluster1.e2e.bos.redhat.com. IN A 10.19.3.28
~~~

#### **Agents**

We need some hardware that will be joining the Hosted Cluster as workers. There is no specific order for this operation, meaning that you can provision the agents before or after creating the Hosted Cluster. In this case, we will create the agents beforehand.

1. Since we will have our own namespace to store objects related to this Hosted Cluster, we first need to patch the `Provisioning` configuration. We will configure metal3 to watch `BaremetalHosts` in every namespace, and we will disable virtual media over TLS since our hardware has issues with this.

    ~~~sh
    oc patch provisioning provisioning-configuration --type merge -p '{"spec":{"watchAllNamespaces": true, "disableVirtualMediaTLS": true }}'
    ~~~

2. Next, we can create the namespace.

    ~~~sh
    export NAMESPACE=hypercluster1
    oc create namespace $NAMESPACE
    ~~~

3. We need a secret where we will store our pull secret.

    ~~~sh
    cat << EOF | oc apply -n $NAMESPACE -f -
    apiVersion: v1
    kind: Secret
    type: kubernetes.io/dockerconfigjson
    metadata:
      name: mavazque-pullsecret
      namespace: $NAMESPACE
    data:
      .dockerconfigjson: <redacted>
    ~~~

4. An Assisted Installer ISO is required for booting our nodes, we will get one via a `InfraEnv`.

    ~~~sh
    cat << EOF | oc apply -n $NAMESPACE -f -
    apiVersion: agent-install.openshift.io/v1beta1
    kind: InfraEnv
    metadata:
      name: hypershift-cluster1-agents
      namespace: $NAMESPACE
    spec:
      additionalNTPSources:
        - "10.19.3.4"
        - "clock.corp.redhat.com"
      pullSecretRef:
        name: mavazque-pullsecret
      sshAuthorizedKey: ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDUetMOs+ShTfPkQ6s+SiSTmlKXzS8YJNEwjVJSDjSpdJQ7iTRBKK67wsdX0YQoebMkGGBQ7sX2RnMD1fIl6a5Nsl38IsQ2gjR4t5r0B5zjtiT1NEzXLBb+DL8aIU8MtocPLh21GLv6IIoIjhsIHrHX3u5+gn19uXydHZsgK9BlrTF55udjcdAlECgzRqEmPQdPiGfN6UfWbwqFMpl3uTQi/itfbJDywhQyXRhfjj+vAeeO4FoRwP9jWi9Om7FF2xMf/Gdrwfj33460dk90phZgAVVbffPxXMt+GSFObwlMxhBeQUTi5pgoKODXrVrEBN+b28hSooHPUk3CxSL6vueseWDT4dDgU7nopzkcvhWJQHPRYrkQVQgE4iFv9sMVbLM1zAb7BuugBLD3b8PZqzim2aJKupJypfv42jssj2vwvo/gLJCw92hjbaAYI8r7y0/gynOBcrKREoLqHK0oHkzWAOLndqgtMyjhDgAqRJOUQ+A27mUUNAQmSXwqRG2xlZ8= root@mavazque-virt.cloud.lab.eng.bos.redhat.com
    EOF
    ~~~

> :information_source: `infraenvs.agent-install.openshift.io` label is used to specify which `InfraEnv` is used to boot the `BMHs`.

5. At this point we will have our iso with the Agent ready to discover our nodes, the next step is creating the `BaremetalHosts`.

    ~~~sh
    cat <<EOF | oc apply -n $NAMESPACE -f -
    ---
    apiVersion: v1
    kind: Secret
    metadata:
      name: worker0
      namespace: $NAMESPACE
    data:
      username: "bm90YXVzZXI="
      password: "bm90YXB3ZA=="
    type: Opaque
    ---
    apiVersion: metal3.io/v1alpha1
    kind: BareMetalHost
    metadata:
      name: worker0
      namespace: $NAMESPACE
      labels:
        infraenvs.agent-install.openshift.io: "hypershift-cluster1-agents"
      annotations:
        inspect.metal3.io: disabled
        bmac.agent-install.openshift.io/hostname: "openshift-worker-0"
        bmac.agent-install.openshift.io/role: "worker"
    spec:
      online: true
      bootMACAddress: ec:f4:bb:ed:6c:48
      automatedCleaningMode: disabled
      rootDeviceHints:
        deviceName: /dev/sda
      bmc:
        address: idrac-virtualmedia://10.19.136.22/redfish/v1/Systems/System.Embedded.1
        credentialsName: worker0
        disableCertificateVerification: true
    ---
    apiVersion: v1
    kind: Secret
    metadata:
      name: worker1
      namespace: $NAMESPACE
    data:
      username: "bm90YXVzZXI="
      password: "bm90YXB3ZA=="
    type: Opaque
    ---
    apiVersion: metal3.io/v1alpha1
    kind: BareMetalHost
    metadata:
      name: worker1
      namespace: $NAMESPACE
      labels:
        infraenvs.agent-install.openshift.io: "hypershift-cluster1-agents"
      annotations:
        inspect.metal3.io: disabled
        bmac.agent-install.openshift.io/hostname: "openshift-worker-1"
        bmac.agent-install.openshift.io/role: "worker"
    spec:
      online: true
      bootMACAddress: ec:f4:bb:ed:83:50
      automatedCleaningMode: disabled
      rootDeviceHints:
        deviceName: /dev/sda
      bmc:
        address: idrac-virtualmedia://10.19.136.23/redfish/v1/Systems/System.Embedded.1
        credentialsName: worker1
        disableCertificateVerification: true
    ---
    apiVersion: v1
    kind: Secret
    metadata:
      name: worker2
      namespace: $NAMESPACE
    data:
      username: "bm90YXVzZXI="
      password: "bm90YXB3ZA=="
    type: Opaque
    ---
    apiVersion: metal3.io/v1alpha1
    kind: BareMetalHost
    metadata:
      name: worker2
      namespace: $NAMESPACE
      labels:
        infraenvs.agent-install.openshift.io: "hypershift-cluster1-agents"
      annotations:
        inspect.metal3.io: disabled
        bmac.agent-install.openshift.io/hostname: "openshift-worker-2"
        bmac.agent-install.openshift.io/role: "worker"
    spec:
      online: true
      bootMACAddress: ec:f4:bb:ed:6f:e8
      automatedCleaningMode: disabled
      rootDeviceHints:
        deviceName: /dev/sda
      bmc:
        address: idrac-virtualmedia://10.19.136.24/redfish/v1/Systems/System.Embedded.1
        credentialsName: worker2
        disableCertificateVerification: true
    EOF
    ~~~

6. Metal3 will boot the servers with the assisted installer ISO and eventually we will get the agents ready to be installed.

    ~~~sh
    oc get -n $NAMESPACE agent,bmh

    NAME                                                                    CLUSTER   APPROVED   ROLE     STAGE
    agent.agent-install.openshift.io/65d7ae64-2758-4677-9a5b-ee9fd8396014             true       worker   
    agent.agent-install.openshift.io/a027a342-2390-4be6-869b-5e7dff2bc3c6             true       worker   
    agent.agent-install.openshift.io/a21d22d1-f5d6-4aae-aa9c-ea4cac523bec             true       worker   

    NAME                              STATE         CONSUMER   ONLINE   ERROR   AGE
    baremetalhost.metal3.io/worker0   provisioned              true             7m47s
    baremetalhost.metal3.io/worker1   provisioned              true             7m47s
    baremetalhost.metal3.io/worker2   provisioned              true             7m47s
    ~~~

7. The Agents should be in known-unbound state t.

    ~~~sh
    oc get agent -n $NAMESPACE -o jsonpath='{range .items[*]}BMH: {@.metadata.labels.agent-install\.openshift\.io/bmh} Agent: {@.metadata.name} State: {@.status.debugInfo.state}{"\n"}{end}'

    BMH: worker0 Agent: 65d7ae64-2758-4677-9a5b-ee9fd8396014 State: known-unbound
    BMH: worker1 Agent: a027a342-2390-4be6-869b-5e7dff2bc3c6 State: known-unbound
    BMH: worker2 Agent: a21d22d1-f5d6-4aae-aa9c-ea4cac523bec State: known-unbound
    ~~~

8. Now our nodes are ready to join a Hosted Cluster.

### **Creating the Hosted Cluster**

In the previous section we got our nodes up and running, next is creating the Hosted Cluster and join those nodes to the Hosted Cluster.

1. We will use the `hypershift` binary to render the required objects.

    > :information_source: We can provide the release to use for our Hosted Cluster via the `--release-image` parameter.

    ~~~sh
    export CLUSTERNAME=hypercluster1
    export BASEDOMAIN=e2e.bos.redhat.com
    hypershift create cluster agent --render --name $CLUSTERNAME --base-domain $BASEDOMAIN --pull-secret ${HOME}/pull_secret.json --ssh-key ${HOME}/.ssh/id_rsa.pub --agent-namespace $NAMESPACE --namespace $NAMESPACE --release-image=quay.io/openshift-release-dev/ocp-release:4.11.0-rc.1-x86_64 > hypercluster1.yaml
    # Add the MachineNetwork CIDR to the Hosted Cluster file
    sed -i "s/    machineCIDR: \"\"/    machineCIDR: \"10.19.3.0\/26\"/" hypercluster1.yaml
    ~~~

2. Inside the `hypercluster1.yaml` we will have all the required objects to deploy the Hosted Cluster. Such output has been [included in the assets folder](../assets/hypercluster1.yaml) as a reference.

3. Now it's time to create the Hosted Cluster.

    ~~~sh
    oc apply -f hypercluster1.yaml
    ~~~

4. A new namespace will be created by HyperShift using the following naming `namespace-clustername`, inside this namespace we will have our Hosted Control Plane running:

    > :information_source: Since we're using the Agent provider, we got the `capi-provider` deployed.

    ~~~sh
    oc -n $NAMESPACE-$CLUSTERNAME get pods
    NAME                                              READY   STATUS    RESTARTS   AGE
    capi-provider-69854b9d46-qbm5l                    1/1     Running   0          9m40s
    catalog-operator-55ff45455f-5ltw7                 2/2     Running   0          8m18s
    certified-operators-catalog-76df8d98d8-x9rjl      1/1     Running   0          8m18s
    cluster-api-6cc46684b5-dznnx                      1/1     Running   0          9m40s
    cluster-autoscaler-67fb87fc66-7sn2c               1/1     Running   0          9m
    cluster-network-operator-545bc59bdd-rkdh7         1/1     Running   0          8m19s
    cluster-policy-controller-6b9664d484-68982        1/1     Running   0          8m19s
    cluster-version-operator-79c74c78f-vxsxh          1/1     Running   0          8m19s
    community-operators-catalog-67ccbfcf68-l6bhd      1/1     Running   0          8m18s
    control-plane-operator-6c44f7f768-jv6tk           1/1     Running   0          9m39s
    etcd-0                                            1/1     Running   0          9m1s
    hosted-cluster-config-operator-6c987c79bc-hll57   1/1     Running   0          8m18s
    ignition-server-6d448bb47c-jkjdp                  1/1     Running   0          9m9s
    ingress-operator-6b55c88bd4-cn4d6                 2/2     Running   0          8m19s
    konnectivity-agent-5895d46b95-vlxrd               1/1     Running   0          9m
    konnectivity-server-57f55d955-2t924               1/1     Running   0          9m1s
    kube-apiserver-84b998449b-nklbg                   3/3     Running   0          9m
    kube-controller-manager-5546f6c4d8-p9nml          1/1     Running   0          8m30s
    kube-scheduler-746c4db68f-xqwc6                   1/1     Running   0          8m30s
    machine-approver-57c97c95c8-7lzfb                 1/1     Running   0          9m
    oauth-openshift-7675445975-xcxn5                  1/1     Running   0          7m41s
    olm-operator-5d485bcc7-bdxgw                      2/2     Running   0          8m17s
    openshift-apiserver-5dff7495b9-mn5qx              2/2     Running   0          8m30s
    openshift-controller-manager-5ddcb7cc8-xg9hq      1/1     Running   0          8m19s
    openshift-oauth-apiserver-77fd775fd5-gq6lj        1/1     Running   0          8m19s
    packageserver-77478d4688-9szm7                    2/2     Running   0          8m17s
    redhat-marketplace-catalog-784c76b988-xn696       1/1     Running   0          8m18s
    redhat-operators-catalog-5dbcdf64cf-6mgzw         1/1     Running   0          8m18s
    ~~~

5. We can generate the kubeconfig and try access the new cluster.

    > :information_source: We have a working control plane, but we still need compute nodes to get the cluster installation finished.

    ~~~sh
    hypershift create kubeconfig > $CLUSTERNAME.kubeconfig
    oc --kubeconfig $CLUSTERNAME.kubeconfig get clusterversion,nodes

    NAME                                         VERSION   AVAILABLE   PROGRESSING   SINCE   STATUS
    clusterversion.config.openshift.io/version             False       True          9m31s   Working towards 4.11.0-rc.1: 522 of 574 done (90% complete)
    ~~~

6. The time to add workers to our Hosted Cluster has come. We will scale the NodePool to 2 replicas. This will cause two agents to get installed and join the cluster.

    :information_source: NodePools can be scaled up and down.

    ~~~sh
    oc scale nodepool/$CLUSTERNAME -n $NAMESPACE --replicas=2
    ~~~

7. We can see the agents moving through different states.

    > :information_source: States will be `binding -> discoverying -> insufficient -> installing -> installing-in-progress -> added-to-existing-cluster

    ~~~sh
    oc get agent -n $NAMESPACE -o jsonpath='{range .items[*]}BMH: {@.metadata.labels.agent-install\.openshift\.io/bmh} Agent: {@.metadata.name} State: {@.status.debugInfo.state}{"\n"}{end}'

    BMH: worker0 Agent: 65d7ae64-2758-4677-9a5b-ee9fd8396014 State: installing-in-progress
    BMH: worker1 Agent: a027a342-2390-4be6-869b-5e7dff2bc3c6 State: known-unbound
    BMH: worker2 Agent: a21d22d1-f5d6-4aae-aa9c-ea4cac523bec State: installing
    ~~~

8. Once the agents are added to an existing cluster, eventually they will become nodes of our Hosted Cluster:

    ~~~sh
    oc --kubeconfig $CLUSTERNAME.kubeconfig get nodes

    NAME                 STATUS   ROLES    AGE    VERSION
    openshift-worker-0   Ready    worker   3m5s   v1.24.0+2dd8bb1
    openshift-worker-2   Ready    worker   2m8s   v1.24.0+2dd8bb1
    ~~~

9. If we look again at the cluster version and the cluster operators we will see the installation is completed now.

    > :information_source: You may need to update your ingress wildcard record to get the Ingress cluster operator working.

    ~~~sh
    oc --kubeconfig $CLUSTERNAME.kubeconfig get clusterversion,co
    
    NAME                                         VERSION   AVAILABLE   PROGRESSING   SINCE   STATUS
    clusterversion.config.openshift.io/version             False       True          28m     Cluster version is 4.11.0-rc.1

    NAME                                                                           VERSION       AVAILABLE   PROGRESSING   DEGRADED   SINCE   MESSAGE
    clusteroperator.config.openshift.io/console                                    4.11.0-rc.1   True        False         False      4m6s    
    clusteroperator.config.openshift.io/csi-snapshot-controller                    4.11.0-rc.1   True        False         False      7m56s   
    clusteroperator.config.openshift.io/dns                                        4.11.0-rc.1   True        False         False      7m38s   
    clusteroperator.config.openshift.io/image-registry                             4.11.0-rc.1   True        False         False      8m5s   
    clusteroperator.config.openshift.io/ingress                                    4.11.0-rc.1   True        False         False      28m     
    clusteroperator.config.openshift.io/insights                                   4.11.0-rc.1   True        False         False      8m34s   
    clusteroperator.config.openshift.io/kube-apiserver                             4.11.0-rc.1   True        False         False      29m     
    clusteroperator.config.openshift.io/kube-controller-manager                    4.11.0-rc.1   True        False         False      29m     
    clusteroperator.config.openshift.io/kube-scheduler                             4.11.0-rc.1   True        False         False      29m     
    clusteroperator.config.openshift.io/kube-storage-version-migrator              4.11.0-rc.1   True        False         False      7m57s   
    clusteroperator.config.openshift.io/monitoring                                 4.11.0-rc.1   True        False         False      6m21s   
    clusteroperator.config.openshift.io/network                                    4.11.0-rc.1   True        False         False      8m38s   
    clusteroperator.config.openshift.io/openshift-apiserver                        4.11.0-rc.1   True        False         False      29m     
    clusteroperator.config.openshift.io/openshift-controller-manager               4.11.0-rc.1   True        False         False      29m     
    clusteroperator.config.openshift.io/openshift-samples                          4.11.0-rc.1   True        False         False      7m7s    
    clusteroperator.config.openshift.io/operator-lifecycle-manager                 4.11.0-rc.1   True        False         False      28m     
    clusteroperator.config.openshift.io/operator-lifecycle-manager-catalog         4.11.0-rc.1   True        False         False      29m     
    clusteroperator.config.openshift.io/operator-lifecycle-manager-packageserver   4.11.0-rc.1   True        False         False      29m     
    clusteroperator.config.openshift.io/service-ca                                 4.11.0-rc.1   True        False         False      8m31s   
    clusteroperator.config.openshift.io/storage                                    4.11.0-rc.1   True        False         False      8m34s   
    ~~~

### **Enabling Node Auto-Scaling for the Hosted Cluster**

Auto-scaling can be enabled, if we enable auto-scaling when more capacity is required in our Hosted Cluster a new Agent will be installed (providing that we have spare agents). In order to enable auto-scaling we can run the following command:

> :information_source: In this case the minimum nodes will be 2 and the maximum 5.

~~~sh
oc -n $NAMESPACE patch nodepool $CLUSTERNAME --type=json -p '[{"op": "remove", "path": "/spec/replicas"},{"op":"add", "path": "/spec/autoScaling", "value": { "max": 5, "min": 2 }}]'
~~~

When the capacity is not required anymore, after 10 minutes the agent will be decommissioned and placed in the spare queue again.

1. Let's create a workload that requires a new node.

    ~~~sh
    cat <<EOF | oc --kubeconfig $CLUSTERNAME.kubeconfig apply -f -
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      creationTimestamp: null
      labels:
        app: reversewords
      name: reversewords
      namespace: default
    spec:
      replicas: 40
      selector:
        matchLabels:
          app: reversewords
      strategy: {}
      template:
        metadata:
          creationTimestamp: null
          labels:
            app: reversewords
        spec:
          containers:
          - image: quay.io/mavazque/reversewords:latest
            name: reversewords
            resources:
              requests:
                memory: 2Gi
    status: {}
    EOF
    ~~~

2. We will see the remaining agent starts getting deployed.

    ~~~sh
    oc get agent -n $NAMESPACE -o jsonpath='{range .items[*]}BMH: {@.metadata.labels.agent-install\.openshift\.io/bmh} Agent: {@.metadata.name} State: {@.status.debugInfo.state}{"\n"}{end}'

    BMH: worker0 Agent: 65d7ae64-2758-4677-9a5b-ee9fd8396014 State: added-to-existing-cluster
    BMH: worker1 Agent: a027a342-2390-4be6-869b-5e7dff2bc3c6 State: discovering
    BMH: worker2 Agent: a21d22d1-f5d6-4aae-aa9c-ea4cac523bec State: added-to-existing-cluster
    ~~~

3. If we check the nodes we will see a new one joined the cluster.

    > :information_source: We got worker-1 added to the cluster

    ~~~sh
    oc --kubeconfig $CLUSTERNAME.kubeconfig get nodes

    NAME                 STATUS   ROLES    AGE   VERSION
    openshift-worker-0   Ready    worker   36m   v1.24.0+2dd8bb1
    openshift-worker-1   Ready    worker   34s   v1.24.0+2dd8bb1
    openshift-worker-2   Ready    worker   35m   v1.24.0+2dd8bb1
    ~~~

4. If we delete the workload and wait 10 minutes the node will be removed.

    ~~~sh
    oc --kubeconfig $CLUSTERNAME.kubeconfig -n default delete deployment reversewords
    ~~~

5. After 10 minutes.

    ~~~sh
    oc --kubeconfig $CLUSTERNAME.kubeconfig get nodes

    NAME                 STATUS   ROLES    AGE   VERSION
    openshift-worker-0   Ready    worker   56m   v1.24.0+2dd8bb1
    openshift-worker-2   Ready    worker   55m   v1.24.0+2dd8bb1
    ~~~

    ~~~sh
    oc get agent -n $NAMESPACE -o jsonpath='{range .items[*]}BMH: {@.metadata.labels.agent-install\.openshift\.io/bmh} Agent: {@.metadata.name} State: {@.status.debugInfo.state}{"\n"}{end}'

    BMH: worker0 Agent: 65d7ae64-2758-4677-9a5b-ee9fd8396014 State: added-to-existing-cluster
    BMH: worker1 Agent: a027a342-2390-4be6-869b-5e7dff2bc3c6 State: known-unbound
    BMH: worker2 Agent: a21d22d1-f5d6-4aae-aa9c-ea4cac523bec State: added-to-existing-cluster
    ~~~