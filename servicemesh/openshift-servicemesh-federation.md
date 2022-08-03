# OpenShift Service Mesh Federation across Clusters

This document describes how to federate two different Service Mesh control planes running on different OpenShift clusters.

## Versions used

* OCP v4.11
* OpenShift Service Mesh Operator v2.2.1
* OpenShift Kiali Operator v1.48.1
* OpenShift Jaeger Operator v1.34.1-5
* OpenShift ElasticSearch Operator v5.4.3
* OpenShift MetalLB Operator v4.11

## Pre-requisites

Before federating the Service Meshes we need to get the OpenShift Service Mesh Operator deployed, this operator is a bit tricky to install since it requires other operators to be deployed first, so the order you need to follow is the one below:

> :information_source: Wait for the operator installation to finish before moving to the next one.

1. Elastic Search Operator
2. Jaeger Operator
3. Kiali Operator
4. Service Mesh Operator

At this point you should have all four operators running, before deploying the Service Mesh Control Plane we are going to deploy the MetalLB Operator which is required to provide LoadBalancer services for bare metal clusters.

> :information_source: If your cluster has a cloud provider that allows the creation of LoadBalancer type services without MetalLB you can skip this.

Once the operator has been installed you need to create an IPAddressPool for each cluster, below example files from our environment:

1. MetalLB Operand

    ~~~yaml
    apiVersion: metallb.io/v1beta1
    kind: MetalLB
    metadata:
      name: metallb
      namespace: openshift-metallb
    ~~~

2. IPAddressPool

    ~~~yaml
    apiVersion: metallb.io/v1beta1
    kind: IPAddressPool
    metadata:
      name: l2-pool
      namespace: openshift-operators
    spec:
      addresses:
      - 10.19.3.29-10.19.3.31
    ~~~

3. L2Advertisement

    ~~~yaml
    apiVersion: metallb.io/v1beta1
    kind: L2Advertisement
    metadata:
      name: l2-pool
      namespace: openshift-operators
    spec:
      ipAddressPools:
      - l2-pool
    ~~~

## Deploying the OpenShift ServiceMesh Control Planes

Now it's time to deploy the `ServiceMeshControlPlane` objects in our two clusters we plan to federate.

**Cluster 1 (Blue Cluster)**

1. Create the namespace for the mesh

    ~~~sh
    oc create namespace blue-mesh-system
    ~~~

2. Create the service mesh control plane

    ~~~yaml
    apiVersion: maistra.io/v2
    kind: ServiceMeshControlPlane
    metadata:
      name: blue-mesh
      namespace: blue-mesh-system
    spec:
      version: v2.1
      runtime:
        defaults:
          container:
            imagePullPolicy: Always
      gateways:
        additionalEgress:
          egress-green-mesh:
            enabled: true
            requestedNetworkView:
            - green-network
            routerMode: sni-dnat
            service:
              metadata:
                labels:
                  federation.maistra.io/egress-for: egress-green-mesh
              ports:
              - port: 15443
                name: tls
              - port: 8188
                name: http-discovery  #note HTTP here
        additionalIngress:
          ingress-green-mesh:
            enabled: true
            routerMode: sni-dnat
            service:
              type: LoadBalancer
              metadata:
                labels:
                  federation.maistra.io/ingress-for: ingress-green-mesh
              ports:
              - port: 15443
                name: tls
              - port: 8188
                name: https-discovery  #note HTTPS here
      security:
        trust:
          domain: blue-mesh.local
    ~~~

3. Wait for the control plane to be ready

    ~~~sh
    oc -n blue-mesh-system get smcp

    NAME        READY   STATUS            PROFILES      VERSION   AGE
    blue-mesh   10/10   ComponentsReady   ["default"]   2.1.4     118s
    ~~~

**Cluster2 (Green Cluster)**

1. Create the namespace for the mesh

    ~~~sh
    oc create namespace green-mesh-system
    ~~~

2. Create the service mesh control plane

    ~~~yaml
    apiVersion: maistra.io/v2
    kind: ServiceMeshControlPlane
    metadata:
      name: green-mesh
      namespace: green-mesh-system
    spec:
      version: v2.1
      runtime:
        defaults:
          container:
            imagePullPolicy: Always
      gateways:
        additionalEgress:
          egress-blue-mesh:
            enabled: true
            requestedNetworkView:
            - blue-network
            routerMode: sni-dnat
            service:
              metadata:
                labels:
                  federation.maistra.io/egress-for: egress-blue-mesh
              ports:
              - port: 15443
                name: tls
              - port: 8188
                name: http-discovery  #note HTTP here
        additionalIngress:
          ingress-blue-mesh:
            enabled: true
            routerMode: sni-dnat
            service:
              type: LoadBalancer
              metadata:
                labels:
                  federation.maistra.io/ingress-for: ingress-blue-mesh
              ports:
              - port: 15443
                name: tls
              - port: 8188
                name: https-discovery  #note HTTPS here
      security:
        trust:
          domain: green-mesh.local
    ~~~

3. Wait for the control plane to be ready

    ~~~sh
    oc -n green-mesh-system get smcp

    NAME         READY   STATUS            PROFILES      VERSION   AGE
    green-mesh   10/10   ComponentsReady   ["default"]   2.1.4     118s
    ~~~

## Federating the OpenShift ServiceMesh Control Planes

Now we have two independent service meshes, one in each cluster. Now it's time to make them aware of each other.

We need to start by getting the CA used by each cluster, since we need clusters to trust the CA of each other.

1. Get CA for Cluster1 (Blue)

    ~~~sh
    oc -n blue-mesh-system get cm istio-ca-root-cert -o jsonpath='{.data.root-cert\.pem}'
    ~~~

2. Get CA for Cluster2 (Green)

    ~~~sh
    oc -n green-mesh-system get cm istio-ca-root-cert -o jsonpath='{.data.root-cert\.pem}'
    ~~~

3. Create a ConfigMap with cluster2's CA in cluster1

    ~~~sh
    cat <<EOF | oc -n blue-mesh-system apply -f -
    kind: ConfigMap
    apiVersion: v1
    metadata:
      name: green-mesh-ca-root-cert
      namespace: blue-mesh-system
    data:
      root-cert.pem: |-
        <OUTPUT FROM STEP 2>
    ~~~

4. Create a ConfigMap with cluster1's CA in cluster2

    ~~~sh
    cat <<EOF | oc -n green-mesh-system apply -f -
    kind: ConfigMap
    apiVersion: v1
    metadata:
      name: blue-mesh-ca-root-cert
      namespace: green-mesh-system
    data:
      root-cert.pem: |-
        <OUTPUT FROM STEP 1>
    ~~~

Now that we have the CAs in place, next step is getting the LoadBalancer service endpoints for both clusters and create the ServiceMeshPeer resources.

1. Get cluster1's ingress for green mesh LoadBalancer endpoint

    ~~~sh
    oc -n blue-mesh-system get svc ingress-green-mesh -o jsonpath='{.status.loadBalancer.ingress[*].ip}'
    ~~~

2. Get cluster2's ingress for blue mesh LoadBalancer endpoint

    ~~~sh
    oc -n green-mesh-system get svc ingress-blue-mesh -o jsonpath='{.status.loadBalancer.ingress[*].ip}'
    ~~~

3. Create ServiceMeshPeer in cluster1

    ~~~sh
    cat << EOF | oc -n blue-mesh-system apply -f -
    kind: ServiceMeshPeer
    apiVersion: federation.maistra.io/v1
    metadata:
      name: green-mesh
      namespace: blue-mesh-system
    spec:
      remote:
        addresses:
         - <OUTPUT FROM STEP 2>
        discoveryPort: 8188
        servicePort: 15443
      gateways:
        ingress:
          name: ingress-green-mesh
        egress:
          name: egress-green-mesh
      security:
        trustDomain: green-mesh.local
        clientID: green-mesh.local/ns/green-mesh-system/sa/egress-blue-mesh-service-account
        certificateChain:
          kind: ConfigMap
          name: green-mesh-ca-root-cert
    EOF
    ~~~

4. Create ServiceMeshPeer in cluster2

    ~~~sh
    cat << EOF | oc -n green-mesh-system apply -f -
    kind: ServiceMeshPeer
    apiVersion: federation.maistra.io/v1
    metadata:
      name: blue-mesh
      namespace: green-mesh-system
    spec:
      remote:
        addresses:
         - <OUTPUT FROM STEP 1>
        discoveryPort: 8188
        servicePort: 15443
      gateways:
        ingress:
          name: ingress-blue-mesh
        egress:
          name: egress-blue-mesh
      security:
        trustDomain: blue-mesh.local
        clientID: blue-mesh.local/ns/blue-mesh-system/sa/egress-green-mesh-service-account
        certificateChain:
          kind: ConfigMap
          name: blue-mesh-ca-root-cert
    ~~~

5. At this point we should have both ServiceMeshes interconnected

    1. Get status for ServiceMeshPeer in cluster1

        ~~~sh
        oc -n blue-mesh-system get servicemeshpeer green-mesh -o jsonpath='{.status}' | jq

        {
          "discoveryStatus": {
            "active": [
              {
                "pod": "istiod-blue-mesh-ff6fdf966-qk8md",
                "remotes": [
                  {
                    "connected": true,
                    "lastConnected": "2022-08-01T18:01:48Z",
                    "lastFullSync": "2022-08-02T13:26:48Z",
                    "source": "10.134.1.10"
                  }
                ],
                "watch": {
                  "connected": true,
                  "lastConnected": "2022-08-01T18:02:15Z",
                  "lastDisconnectStatus": "503 Service Unavailable",
                  "lastFullSync": "2022-08-02T13:30:26Z"
                }
              }
            ]
          }
        }
        ~~~

    2. Get status for ServiceMeshPeer in cluster2

        ~~~sh
        oc -n green-mesh-system get servicemeshpeer blue-mesh -o jsonpath='{.status}' | jq

        {
          "discoveryStatus": {
            "active": [
              {
                "pod": "istiod-green-mesh-594f485c4c-7k57m",
                "remotes": [
                  {
                    "connected": true,
                    "lastConnected": "2022-08-01T18:02:15Z",
                    "lastFullSync": "2022-08-02T13:30:26Z",
                    "source": "10.132.1.10"
                  }
                ],
                "watch": {
                  "connected": true,
                  "lastConnected": "2022-08-01T18:01:48Z",
                  "lastDisconnectStatus": "503 Service Unavailable",
                  "lastFullSync": "2022-08-02T13:31:48Z"
                }
              }
            ]
          }
        }
        ~~~

6. We are done with the federation, both meshes have been federated, now we can start deploying services across clusters.

## Deploying Services in the Service Mesh

We will start by deploying a simple application in both of our meshes. You can find the app yaml files in [this folder](./assets/openshift-servicemesh-federation/).

1. First, we need to add namespaces for our applications using the ServiceMesh to the `ServiceMeshMemberRoll`. Let's create the namespaces on each cluster.

    1. Create the ServiceMeshMemberRoll for cluster1

        ~~~sh
        cat <<EOF | oc -n blue-mesh-system apply -f -
        apiVersion: maistra.io/v1
        kind: ServiceMeshMemberRoll
        metadata:
          name: default
          namespace: blue-mesh-system
        spec:
          members:
            - nfs-app-istio
        EOF
        ~~~

    2. Create the ServiceMeshMemberRoll for cluster2

        ~~~sh
        cat <<EOF | oc -n green-mesh-system apply -f -
        apiVersion: maistra.io/v1
        kind: ServiceMeshMemberRoll
        metadata:
          name: default
          namespace: green-mesh-system
        spec:
          members:
            - nfs-app-istio
        EOF
        ~~~

2. We can now go ahead and deploy our application on both clusters

    1. Deploy the application in cluster1

        ~~~sh
        oc create ns nfs-app-istio
        oc apply -f app-blue.yaml
        ~~~

    2. Deploy the application in cluster2

        ~~~sh
        oc create ns nfs-app-istio
        oc apply -f app-green.yaml
        ~~~

3. We can check the application pods on both clusters

    1. Check application in cluster1

        > :information_source: You have to see 2/2 ready containers, that means that the envoy sidecar was injected.

        ~~~sh
        oc -n nfs-app-istio get pods

        NAME                        READY   STATUS    RESTARTS   AGE
        dokuwiki-7947b79754-m8jsv   2/2     Running   0          24m
        ~~~

    2. Check application in cluster2

        ~~~sh
        oc -n nfs-app-istio get pods

        NAME                        READY   STATUS    RESTARTS   AGE
        dokuwiki-6d65c5967c-d59g6   2/2     Running   0          25m
        ~~~

4. We should be able to access the app by using the Istio Ingress Gateway + the application virtualservice's prefixes we configured:

    1. Get the Istio Ingress Gateway from cluster 1

        ~~~sh
        oc -n blue-mesh-system get route istio-ingressgateway -o jsonpath='{.spec.host}'

        istio-ingressgateway-blue-mesh-system.apps.cluster1.example.com
        ~~~

    2. Access the app in cluster 1

        ~~~text
        http://istio-ingressgateway-blue-mesh-system.apps.cluster1.example.com/dokuwiki
        ~~~

    3. Get the Istio Ingress Gateway from cluster 4

        ~~~sh
        oc -n green-mesh-system get route istio-ingressgateway -o jsonpath='{.spec.host}'

        istio-ingressgateway-green-mesh-system.apps.cluster2.example.com
        ~~~

    4. Access the app in cluster 2

        ~~~text
        http://istio-ingressgateway-green-mesh-system.apps.cluster2.example.com/dokuwiki
        ~~~

Now we have our application running on the two meshes, in the next section we will see how we can import/export services from the different federated meshes.

## Exporting / Importing a Service from a Federated Mesh

We will use `ExportedServiceSet` resource to export the `Dokuwiki` service from our blue-mesh. After that, we will use `ImportedServiceSet` to import the `Dokuwiki` service from blue-mesh into the green-mesh.

There are a few considerations to keep in mind:

* For exported services, their target services will only see traffic from the ingress gateway, not the original requestor (that is, they won’t see the client ID of either the other mesh’s egress gateway or the workload originating the request).
* We can only export services which are visible to the mesh’s namespace (ServiceMeshMemberRoll).
* The name of the ExportedServiceSet must match the ServiceMeshPeer name.

1. Create the `ExportedServiceSet` in cluster1 exporting the dokuwiki service

    ~~~sh
    cat <<EOF | oc -n blue-mesh-system apply -f -
    kind: ExportedServiceSet
    apiVersion: federation.maistra.io/v1
    metadata:
      name: green-mesh
      namespace: blue-mesh-system
    spec:
      exportRules:
      - type: NameSelector
        nameSelector:
          namespace: nfs-app-istio
          name: "dokuwiki"
          alias:
            namespace: nfs-app-istio
            name: dokuwiki
    EOF
    ~~~

2. Check the status:

    ~~~sh
    oc -n blue-mesh-system get exportedserviceset green-mesh -o jsonpath='{.status}' | jq

    {
      "exportedServices": [
        {
          "exportedName": "dokuwiki.nfs-app-istio.svc.green-mesh-exports.local",
          "localService": {
            "hostname": "dokuwiki.nfs-app-istio.svc.cluster.local",
            "name": "dokuwiki",
            "namespace": "nfs-app-istio"
          }
        }
      ]
    }
    ~~~

3. Create the `ImportedServiceSet` in cluster2 importing the dokuwiki service from cluster1

    ~~~sh
    cat <<EOF | oc -n green-mesh-system apply -f -
    kind: ImportedServiceSet
    apiVersion: federation.maistra.io/v1
    metadata:
      name: blue-mesh
      namespace: green-mesh-system
    spec:
      importRules:
      - type: NameSelector
        importAsLocal: false
        nameSelector:
          namespace: nfs-app-istio
          name: dokuwiki
          alias:
            namespace: nfs-app-istio
            name: blue-dokuwiki
    EOF
    ~~~

4. Check the status:

    > :information_source: It can take up to a couple of minutes for the services to be imported.

    ~~~sh
    oc -n green-mesh-system get ImportedServiceSet blue-mesh -o jsonpath='{.status}' | jq


    {
      "importedServices": [
        {
          "exportedName": "dokuwiki.nfs-app-istio.svc.green-mesh-exports.local",
          "localService": {
            "hostname": "blue-dokuwiki.nfs-app-istio.svc.blue-mesh-imports.local",
            "name": "blue-dokuwiki",
            "namespace": "nfs-app-istio"
          }
        }
      ]
    }
    ~~~

Now that the service is imported in the green mesh, we can route traffic to it. Befor doing that let's scale down the dokuwiki deployment in cluster2:

~~~sh
oc -n nfs-app-istio scale deployment dokuwiki --replicas=0
~~~

If we try to access the service in the cluster2, we will get an error:

~~~sh
curl http://istio-ingressgateway-green-mesh-system.apps.cluster2.example.com/dokuwiki

no healthy upstream
~~~

Let's route the traffic to the imported dokuwiki service:

~~~yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: dokuwiki
  namespace: nfs-app-istio
spec:
  gateways:
  - dokuwiki-gateway
  hosts:
  - '*'
  http:
  - match:
    - uri:
        exact: /dokuwiki
    - uri:
        prefix: /lib
    route:
    - destination:
        host: dokuwiki
        port:
          number: 8080
      weight: 0
    - destination:
        host: blue-dokuwiki.nfs-app-istio.svc.blue-mesh-imports.local
        port:
          number: 8080
      weight: 100
~~~

At this point the connections to `http://istio-ingressgateway-green-mesh-system.apps.cluster2.example.com/dokuwiki` should work, but I wasn't able to see it working.