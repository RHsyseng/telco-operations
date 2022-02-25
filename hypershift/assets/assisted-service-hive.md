# **Deploy the Assisted Service and Hive operators on OCP**

This document shows how to deploy the Assisted Service and Hive operators on OCP. 

## **Versions used**

* OCP compact cluster (3 masters) version 4.9.21 (IPI baremetal)
* Assisted Service Operator version v0.2.10
* Hive Operator version v1.2.3490-7e0b248

## **Requisites**

* `cluster:admin` permissions in the OCP cluster where the operators are going to be deployed
* 2 filesystem type Persistent Volumes to store the Assisted Service assets and database

We will leverage [`tasty`](https://github.com/karmab/tasty) to deploy the required operators easily. 

* Install tasty:

~~~sh
curl -s -L https://github.com/karmab/tasty/releases/download/v0.4.0/tasty-linux-amd64 > ./tasty
sudo install -m 0755 -o root -g root ./tasty /usr/local/bin/tasty
~~~

## **Deployment**

* Install the operators:

~~~sh
tasty install assisted-service-operator hive-operator
~~~

* Wait until the operators are properly installed and the CRDs created:

~~~sh
until oc get crd/agentserviceconfigs.agent-install.openshift.io >/dev/null 2>&1 ; do sleep 1 ; done
~~~

* Create the `agentserviceconfig` object:

~~~sh
export DB_VOLUME_SIZE="10Gi"
export FS_VOLUME_SIZE="10Gi"
export OCP_VERSION="4.9"
export ARCH="x86_64"
export OCP_RELEASE_VERSION=$(curl -s https://mirror.openshift.com/pub/openshift-v4/${ARCH}/clients/ocp/latest-${OCP_VERSION}/release.txt | awk '/machine-os / { print $2 }')
export ISO_URL="https://mirror.openshift.com/pub/openshift-v4/dependencies/rhcos/${OCP_VERSION}/latest/rhcos-${OCP_VERSION}.0-${ARCH}-live.${ARCH}.iso"
export ROOT_FS_URL="https://mirror.openshift.com/pub/openshift-v4/dependencies/rhcos/${OCP_VERSION}/latest/rhcos-live-rootfs.${ARCH}.img"

envsubst <<"EOF" | oc apply -f -
apiVersion: agent-install.openshift.io/v1beta1
kind: AgentServiceConfig
metadata:
 name: agent
spec:
  databaseStorage:
    accessModes:
    - ReadWriteOnce
    resources:
      requests:
        storage: ${DB_VOLUME_SIZE}
  filesystemStorage:
    accessModes:
    - ReadWriteOnce
    resources:
      requests:
        storage: ${FS_VOLUME_SIZE}
  osImages:
    - openshiftVersion: "${OCP_VERSION}"
      version: "${OCP_RELEASE_VERSION}"
      url: "${ISO_URL}"
      rootFSUrl: "${ROOT_FS_URL}"
      cpuArchitecture: "${ARCH}"
EOF
~~~

* Wait for the assisted-service pod to be ready:

~~~sh
until oc wait -n assisted-installer $(oc get pods -n assisted-installer -l app=assisted-service -o name) --for condition=Ready --timeout 10s >/dev/null 2>&1 ; do sleep 1 ; done
~~~

Profit!