# **ZTP Remote Worker Nodes at day 0 with Assisted Installer**

:warning: The work exposed here is not supported in any way by Red Hat, this is the result of exploratory work. Use at your own risk.

If you want to see how to add a remote worker node at day 2 with Assisted Installer you can check [this video](https://drive.google.com/file/d/1eaD_eNEd7_MfDvszWYm4DAhBDpA5sUmd/view?usp=sharing) from @karmab.

If you want to see how you can deploy a RWN and a SNO with Assisted Installer you can check [this video](https://drive.google.com/file/d/1xN1Ew3oGHARwqcWqEmxTZrIEf3N_uXGt/view?usp=sharing) from @karmab.


## **Requirements**

* OpenShift Cluster acting as Hub (We tested with 4.9.12)
* RH ACM (We tested with 2.4)
* Hardware with RedFish support (We virtualized hardware with KVM and emulated RedFish with SushyTools)

## **Deployment**

### **Prereqs and Patches**

Before deploying the cluster we need to spawn an Assisted Service instance in our Hub cluster, in order to get it deployed we need to create a `AgentServiceConfig` object. You can use the one below (if you do, change the required parameters to match your environment):

~~~yaml
apiVersion: agent-install.openshift.io/v1beta1
kind: AgentServiceConfig
metadata:
  name: agent
spec:
  databaseStorage:
    storageClassName: fs-lso
    accessModes:
    - ReadWriteOnce
    resources:
      requests:
        storage: 10Gi
  filesystemStorage:
    storageClassName: fs-lso
    accessModes:
    - ReadWriteOnce
    resources:
      requests:
        storage: 20Gi
  osImages:
  - cpuArchitecture: x86_64
    openshiftVersion: "4.8"
    rootFSUrl: https://mirror.openshift.com/pub/openshift-v4/dependencies/rhcos/4.8/4.8.14/rhcos-live-rootfs.x86_64.img
    url: https://mirror.openshift.com/pub/openshift-v4/dependencies/rhcos/4.8/4.8.14/rhcos-4.8.14-x86_64-live.x86_64.iso
    version: 48.84.202109241901-0
  - cpuArchitecture: x86_64
    openshiftVersion: "4.9"
    rootFSUrl: https://mirror.openshift.com/pub/openshift-v4/dependencies/rhcos/4.9/4.9.0/rhcos-live-rootfs.x86_64.img
    url: https://mirror.openshift.com/pub/openshift-v4/dependencies/rhcos/4.9/4.9.0/rhcos-4.9.0-x86_64-live.x86_64.iso
    version: 49.84.202110081407-0
~~~

After a few minutes you should see the Assisted Service running:

~~~sh
oc -n open-cluster-management get pod -l app=assisted-service

NAME                                READY   STATUS    RESTARTS      AGE
assisted-service-58db8dc888-2kqrv   2/2     Running   2 (52m ago)   135m
~~~

Now that we have the AI running, we can proceed with the ZTP cluster deployment, we're going to create a namespace for every cluster we deploy, that means that we need to patch the `Provisioning` config so the BareMetal Operator can read `BaremetalHost` objects created on any namespace. If you don't plan to keep all objects related to a cluster deployment in the same namespace you just need to create the `BaremetalHost` objects inside the `openshift-machine-api` namespace.

~~~sh
oc patch provisioning provisioning-configuration --type merge -p '{"spec":{"watchAllNamespaces": true}}'
~~~

### **Current Limitations**

Since deploying remote workers as a day0 operation is not supported yet by AI, we need to disable some validations that are done by AI before the installation can happen.

1. Create a ConfigMap to configure disabled validations so the installation can start

    ~~~sh
    oc -n open-cluster-management create configmap assisted-service-config --from-literal=DISABLED_HOST_VALIDATIONS=belongs-to-majority-group,belongs-to-machine-cidr
    ~~~
2. Patch the AgentServiceConfig so it reads the configmap and applies the new config

    ~~~sh
    oc -n open-cluster-management patch agentserviceconfig agent -p '{"metadata":{"annotations":{"unsupported.agent-install.openshift.io/assisted-service-configmap":"assisted-service-config"}}}' --type merge
    ~~~

### **Cluster Deployment**

#### **Workarounds**

Since we have a remote worker, we need to take care of the Ingress Operator and make sure that the routers do not fall under that remote worker, in order to do that we add extra manifests where we configure the Ingress Operator so routers run on master nodes. Another component that we don't want to run on the remote worker is `KeepAliveD`, so we remove the static pod definition using an ignition override at the BMH level and a `MachineConfig` and `MachineConfigPool`. You can see extra manifests [here](./assets/ztp-cluster/06_extra_manifests.yaml)

After the cluster is deployed, the routers could be moved to a list of workers matching some labels.

#### **Issues we found**

This section describes issues that we have found during the cluster deployments. Since this is not supported, some of these issues are expected.

**Ingress Operator**

Ingress Operator does not support configuring *complex* MatchinExpressions, for example, if you wanted to configure something like this:

~~~yaml
  nodePlacement:
    nodeSelector:
      matchExpressions:
      - key: kubernetes.io/hostname
        operator: In
        values:
        - "openshift-master-0"
        - "openshift-master-1"
~~~

or

~~~yaml
  nodePlacement:
    nodeSelector:
      matchExpressions:
      - key: node.openshift.io/remotenode
        operator: DoesNotExist
~~~

You would get error messages similar to:

~~~log
2022-01-19T13:25:22.242Z	ERROR	operator.init.controller-runtime.manager.controller.ingress_controller	controller/controller.go:253	Reconciler error	{"name": "default", "namespace": "openshift-ingress-operator", "error": "failed to ensure deployment: failed to build router deployment: ingresscontroller \"default\" has invalid spec.nodePlacement.nodeSelector: operator \"NotIn\" cannot be converted into the old label selector format", "errorCauses": [{"error": "failed to ensure deployment: failed to build router deployment: ingresscontroller \"default\" has invalid spec.nodePlacement.nodeSelector: operator \"DoesNotExist\" cannot be converted into the old label selector format"}]}
~~~

We opened [BugZilla #2043573](https://bugzilla.redhat.com/show_bug.cgi?id=2043573) to try get this issue solved.

**Labeling Nodes during install**

Our first approach was running the routers on worker nodes labeled with a custom label `openshift.io/ingress: true`, in order to get this label configured at Day 0 we tried to add the worker objects with this labels to the extra manifests configmap like this:

~~~yaml
98_worker0_labels.yaml: |
apiVersion: v1
kind: Node
metadata:
  labels:
  # We need to add the role label, otherwise the node won't get a role assigned automatically
    node-role.kubernetes.io/worker: ""
    node.openshift.io/os_id: "rhcos"
    openshift.io/ingress: "true"
  name: openshift-worker-0
spec: {}
~~~

While this approach was tested and worked for UPI deployments, Assisted Installer deployments failed all the time. We assume AI does not expect to have worker nodes added before masters join the cluster and that causes the install to fail.

#### **Deployment**

Now that we have the prereqs and patches ready we can run the cluster deployment, we just need to create all objects inside the [assets/ztp-cluster/](./assets/ztp-cluster/) in our Hub cluster.

You can see the deployment in action [here](https://drive.google.com/file/d/1yDYMsawPBNgjM3zm9-7ZqSHuiUBrOk2S/view?usp=sharing).

### **Ingress and Egress on the Remote Worker Node**

**Ingress**

* OpenShift Router/s running on the master/non-remote worker node/s:
  
  * Ingress to applications running on the remote worker node works just fine. This is expected since the routers are running on the master nodes and from there connection to the remote worker node will happen at SDN level.

* OpenShift Router/s running on the remote worker node/s:

  * Default ingress controller on remote worker node/s:

    * The remote node doesn't have an interface on the network where the IngressVIP is located, and as such, if you try to move ingress there the router pod will start and br-ex will configure the IngressVIP, but ingress will be broken since traffic cannot be properly routed.

  * Sharded ingress on remote node:

    * We configured a sharded ingress controller ([official docs](https://docs.openshift.com/container-platform/4.9/networking/ingress-operator.html#nw-ingress-sharding_configuring-ingress)). The configuration for this ingress controller looks like this:

      ~~~yaml
      apiVersion: operator.openshift.io/v1
      kind: IngressController
      metadata:
        name: rwn
        namespace: openshift-ingress-operator
      spec:
        replicas: 1
        domain: apps-rwn.ztp.e2e.bos.redhat.com
        nodePlacement:
          nodeSelector:
            matchLabels:
              kubernetes.io/hostname: "openshift-worker-2.ztp.e2e.bos.redhat.com"
        routeSelector:
          matchLabels:
            type: rwn-route
      ~~~

    * Since we need to route traffic to our new domain `apps-rwn.ztp.e2e.bos.redhat.com`, we deployed an external HAProxy that redirects connections to the remote worker node/s where the routers for this domain are running.

    * We labeled our OpenShift Routes targetting apps running on remote worker nodes with the label `type: rwn-route` and then the traffic was handled by the OpenShift router running on the remote worker node and the app was accessed successfully.

**Egress**

* **Egress IP from non-RWN machineNetwork for apps running on RWN:**

  * First, we need to label the RWN with k8s.ovn.org/egress-assignable: ""

    ~~~sh
    oc label node openshift-worker-2.ztp.e2e.bos.redhat.com k8s.ovn.org/egress-assignable=""
    ~~~

  * Next we need to create the `EgressIP` configuration:

    ~~~yaml
    apiVersion: k8s.ovn.org/v1
    kind: EgressIP
    metadata:
      name: egressips-rwn
    spec:
      egressIPs:
      - 10.19.3.50
      namespaceSelector:
        matchLabels:
          type: rwn
    ~~~

  * We will see that the EgressIP cannot be configured on the remote worker since the node's br-ex interface is not connected to the network where the egressIP lives in.

  * In order to overcome the above issue, we can label a different node (non-rwn) with the `egress-assignable` label, and then we will be able to host that IP somewhere:

    ~~~sh
    oc label node openshift-worker-0.ztp.e2e.bos.redhat.com k8s.ovn.org/egress-assignable=""
    ~~~

  * Once we get the EgressIP configured we can run a connection from a pod running on a namespace labeled with the label `type: rwn` and scheduled in the RWN, and we will see we connect using the egressIP:

    > **NOTE**: 10.19.3.46 is an IP from the default machine network. 10.19.142.255 is an IP from the RWN network.

    ~~~sh
    $ curl http://10.19.3.46:8000
    $ curl http://10.19.142.255:8000
    ~~~

    > **NOTE**: These are the logs from the HTTP server we're accessing, we can see source IP 10.19.3.50 (the one configured as egressIP)

    ~~~log
    10.19.3.50 - - [28/Feb/2022 17:25:43] "GET / HTTP/1.1" 200 -
    10.19.3.50 - - [28/Feb/2022 17:26:10] "GET / HTTP/1.1" 200 -
    ~~~

  * The traffic will be routed through the non-RWN node in this case.

* **Egress IP from RWN machineNetwork for apps running on RWN**

  * For this test we need to remove the label we added previously:

    ~~~sh
    oc label node openshift-worker-0.ztp.e2e.bos.redhat.com k8s.ovn.org/egress-assignable-
    ~~~

  * And remove the egressIP:

    ~~~sh
    oc delete egressip egressips-rwn
    ~~~

  * Now we create the egressIP with an IP from the RWN network range:

    ~~~yaml
    apiVersion: k8s.ovn.org/v1
    kind: EgressIP
    metadata:
      name: egressips-rwn
    spec:
      egressIPs:
      - 10.19.142.253
      namespaceSelector:
        matchLabels:
          type: rwn
    ~~~

  * Once we get the EgressIP configured we can run a connection from a pod running on a namespace labeled with the label `type: rwn` and scheduled in the RWN, and we will see we connect using the egressIP:

    > **NOTE**: 10.19.3.46 is an IP from the default machine network. 10.19.142.255 is an IP from the RWN network.

    ~~~sh
    $ curl http://10.19.3.46:8000
    $ curl http://10.19.142.255:8000
    ~~~

    > **NOTE**: These are the logs from the HTTP server we're accessing, we can see source IP 10.19.142.253 (the one configured as egressIP)

    ~~~log
    10.19.142.253 - - [28/Feb/2022 17:31:48] "GET / HTTP/1.1" 200 -
    10.19.142.253 - - [28/Feb/2022 17:31:51] "GET / HTTP/1.1" 200 -
    ~~~

  * The traffic will be routed through the RWN node in this case.

* **Egress IP from RWN machineNetwork for apps running on non-RWN**

  * We can run a connection from a pod running on a namespace labeled with the label `type: rwn` and scheduled in a non-RWN node, and we will see we connect using the egressIP:

    > **NOTE**: 10.19.3.46 is an IP from the default machine network. 10.19.142.255 is an IP from the RWN network.

    ~~~sh
    $ curl http://10.19.3.46:8000
    $ curl http://10.19.142.255:8000
    ~~~

    > **NOTE**: These are the logs from the HTTP server we're accessing, we can see source IP 10.19.142.253 (the one configured as egressIP)

    ~~~log
    10.19.142.253 - - [28/Feb/2022 17:35:29] "GET / HTTP/1.1" 200 -
    10.19.142.253 - - [28/Feb/2022 17:35:33] "GET / HTTP/1.1" 200 -
    ~~~

  * The traffic will be routed through the RWN node in this case.
  