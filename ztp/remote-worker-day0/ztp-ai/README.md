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

Before deploying the cluster we need to deploy an Assisted Service instance in our Hub cluster, in order to get it deploy we need to create an `AgentServiceConfig` object. You can use the one below (if you do, change the required parameters to match your environment):

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

Since we have a remote worker, we need to take care of the Ingress Operator and make sure that the routers do not fall under that remote worker, in order to do that we add extra manifests where we configure the Ingress Operator so routers run on master nodes. You can see extra manifests [here](./assets/ztp-cluster/06_extra_manifests.yaml)

After cluster is deploy, the routers could be moved to a list of worker matching some labels. 

#### **Issues we found**

This section describe issues that we have found during the cluster deployments. Since this is not supported some of this issues are expected.

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

~~~
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