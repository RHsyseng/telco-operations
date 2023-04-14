# Gateway API on OpenShift 4.13

This doc covers how to deploy the Gateway API on an OpenShift 4.13 Cluster.

Information in this document is not supported by Red Hat.

Versions used:

- OpenShift v4.13.0-rc.3
- Gateway API v0.6.2
- MetalLB v4.12

The end goal is to be able to create `HTTPRoutes` exposing an application via `HTTP/s`. In the future, as the gateway implementations mature we can explore other ways of exposing our applications like `TCPRoute` or `TLSRoute`, and do cross-namespace references with `ReferenceGrants`.

## Introduction to Gateway API

Gateway API is an open source project managed by the SIG-NETWORK community. It is a collection of resources that model service networking in Kubernetes. These resources - `GatewayClass`, `Gateway`, `HTTPRoute`, `TCPRoute`, `Service`, etc - aim to evolve Kubernetes service networking through expressive, extensible, and role-oriented interfaces that are implemented by many vendors and have broad industry support. <sup>[Source](https://gateway-api.sigs.k8s.io/)</sup>

## Deploying the Gateway API

For this introduction we are deploying the [standard APIs](https://gateway-api.sigs.k8s.io/concepts/versioning/#release-channels-eg-experimental-standard), so we won't get support for `TCPRoute`, `TLSRoute`, etc. Only basic support for `HTTPRoute` will be available.

1. Deploy the Gateway API CRDs and admission server

    ~~~sh
    oc apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v0.6.2/standard-install.yaml
    ~~~

2. If we check the pod created in the `gateway-system` namespace, we will see that the admission server is on `ContainerCreating`:

    ~~~sh
    oc -n gateway-system get pods
    ~~~

    ~~~console
    NAME                                            READY   STATUS              RESTARTS   AGE
    gateway-api-admission-server-546bdb8747-mdzsk   0/1     ContainerCreating   0          74s
    ~~~

3. Pod cannot start because the secret `gateway-api-admission` is not created. That secret gets created by one job, if we check the jobs we will notice that pods are not running for those jobs:

    ~~~sh
    oc -n gateway-system get jobs
    ~~~

    ~~~console
    NAME                          COMPLETIONS   DURATION   AGE
    gateway-api-admission         0/1           4m3s       4m3s
    gateway-api-admission-patch   0/1           4m3s       4m3s
    ~~~

4. These jobs try to run with a `nonroot` UID, but in OpenShift it's required access to a valid `SecurityContextConstraing (SCC)` to be able to do so. We will grant this access to the `ServiceAccount` that runs the jobs:

    ~~~yaml
    securityContext:
      runAsNonRoot: true
      runAsUser: 2000
    ~~~

    ~~~sh
    oc -n gateway-system adm policy add-scc-to-user nonroot-v2 -z gateway-api-admission
    ~~~

5. After a few moments the admission server pod and the job's pod should be okay:

    ~~~sh
    oc -n gateway-system get pods
    ~~~

    ~~~console
    NAME                                            READY   STATUS      RESTARTS   AGE
    gateway-api-admission-patch-r5ghp               0/1     Completed   0          3m12s
    gateway-api-admission-server-546bdb8747-mdzsk   1/1     Running     0          7m22s
    gateway-api-admission-vbt77                     0/1     Completed   0          3m12s
    ~~~

Now we have the Gateway API running, next step is choosing the Gateway API implementation of our choice. You can find a list of current implementations [here](https://gateway-api.sigs.k8s.io/implementations/).

## Deploying the NGinx Gateway Controller

We will be using the NGinx Gateway Controller, you can find the code [here](https://github.com/nginxinc/nginx-kubernetes-gateway).

The instructions to deploy the controller use the commit `918d6506483fb42710a227b4ecb35c9dca43ccc5` which is the content of the `main` branch as of April 14th.

1. Create the namespace where the controller will be deployed:

    ~~~sh
    oc apply -f https://raw.githubusercontent.com/nginxinc/nginx-kubernetes-gateway/918d6506483fb42710a227b4ecb35c9dca43ccc5/deploy/manifests/namespace.yaml
    ~~~

2. Create the `njs-modules`, this is used by NGinx to implement the data plane:

    > **NOTE**: `njs` is a subset of the JavaScript language that allows extending nginx functionality.

    ~~~sh
    curl -L https://raw.githubusercontent.com/nginxinc/nginx-kubernetes-gateway/918d6506483fb42710a227b4ecb35c9dca43ccc5/internal/nginx/modules/src/httpmatches.js -o /tmp/httpmatches.js
    oc -n nginx-gateway create configmap njs-modules --from-file=/tmp/httpmatches.js
    rm -f /tmp/httpmatches.js
    ~~~

3. Create the `GatewayClass` that will use the nginx controller as backend:

    ~~~sh
    oc apply -f https://raw.githubusercontent.com/nginxinc/nginx-kubernetes-gateway/918d6506483fb42710a227b4ecb35c9dca43ccc5/deploy/manifests/gatewayclass.yaml
    ~~~

4. Finally, deploy the NGinx Gateway Controller:

    > **INFO**: Container nginx-gateway is using `ghcr.io/nginxinc/nginx-kubernetes-gateway:edge` which at the time of this writing points to `ghcr.io/nginxinc/nginx-kubernetes-gateway@sha256:9613836a69fdd527faa3635756959b9884d1017d6f193b82b83fe481d74d235e`.

    ~~~sh
    oc apply -f https://raw.githubusercontent.com/nginxinc/nginx-kubernetes-gateway/918d6506483fb42710a227b4ecb35c9dca43ccc5/deploy/manifests/nginx-gateway.yaml
    ~~~

5. Again, the pod won't start. That's caused by the busybox init container that requires running as UID 0. Let's fix it:

    ~~~sh
    oc -n nginx-gateway adm policy add-scc-to-user anyuid -z nginx-gateway
    ~~~

6. After a few moments, the controller pod will be running:

    ~~~sh
    oc -n nginx-gateway get pods
    ~~~

    ~~~console
    NAME                             READY   STATUS    RESTARTS   AGE
    nginx-gateway-6ddb979dbd-mzffs   2/2     Running   0          2m59s
    ~~~

7. We need to expose the gateway controller, we will be using a `LoadBalancer` service for that. In our cluster we are using `MetalLB`.

    > **INFO**: You can read how to deploy MetalLB on the [official docs](https://docs.openshift.com/container-platform/4.12/networking/metallb/about-metallb.html).

    ~~~sh
    oc apply -f https://raw.githubusercontent.com/nginxinc/nginx-kubernetes-gateway/918d6506483fb42710a227b4ecb35c9dca43ccc5/deploy/manifests/service/loadbalancer.yaml
    ~~~

8. We should have a `Service` with an external IP set:

    ~~~sh
    oc -n nginx-gateway get svc
    ~~~

    ~~~console
    NAME            TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)                      AGE
    nginx-gateway   LoadBalancer   172.30.69.152   10.19.3.55    80:32156/TCP,443:31275/TCP   15s
    ~~~

9. In order to be able to expose our applications we need proper DNS resolution, we will be configuring a wildcard record in our DNS server. In this case we're creating a record `*.apps.gateway-api.test.lab` that points to the external IP `10.19.3.55`.

    > **NOTE**: This wildcard will be used for exposing our apps.

    ~~~sh
    dig +short anything.apps.gateway-api.test.lab
    ~~~

    ~~~console
    10.19.3.55
    ~~~

At this point we are ready to start exposing our applications with the NGinx Gateway.

## Exposing applications with the NGinx Gateway

In this section we will go over three scenarios:

1. Expose a simple application via HTTP.
2. Blue/Green scenario with weights.
3. Expose a simple application via HTTPs.

### Exposing a simple app via HTTP

1. Deploy the simple app:

    ~~~sh
    cat <<EOF | oc apply -f -
    ---
    apiVersion: v1
    kind: Namespace
    metadata:
      name: reverse-words
    ---
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: reverse-words-blue
      namespace: reverse-words
      labels:
        app: reverse-words-blue
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: reverse-words-blue
      template:
        metadata:
          labels:
            app: reverse-words-blue
        spec:
          containers:
          - name: reverse-words
            image: quay.io/mavazque/reversewords:0.27
            ports:
            - containerPort: 8080
              name: http
            env:
            - name: RELEASE
              value: "Blue"
            livenessProbe:
              httpGet:
                path: /health
                port: 8080
              initialDelaySeconds: 5
              timeoutSeconds: 2
              periodSeconds: 15
            readinessProbe:
              httpGet:
                path: /health
                port: 8080
              initialDelaySeconds: 10
              timeoutSeconds: 2
              periodSeconds: 15
    ---
    apiVersion: v1
    kind: Service
    metadata:
      labels:
        app: reverse-words-blue
      name: reverse-words-blue
      namespace: reverse-words
    spec:
      ports:
      - port: 8080
        protocol: TCP
        targetPort: http
        name: http
      selector:
        app: reverse-words-blue
      type: ClusterIP
    EOF
    ~~~

2. With the app running we will create a `Gateway` resource pointing to the NGinx Gateway Class created earlier. On top of that, it will only listen for HTTP connections on port `80`.

    > **NOTE**: When creating `HTTPRoutes` in the `reverse-words` namespace we will reference this Gateway and the listener to be used to expose our application. We can have multiple `Gateways` per namespace, for example: One `Gateway` that exposes services using NGinx, another one that uses `HAProxy`, and a third one that uses `F5 Big IP`.

    ~~~sh
    cat <<EOF | oc apply -f -
    apiVersion: gateway.networking.k8s.io/v1beta1
    kind: Gateway
    metadata:
      name: gateway
      namespace: reverse-words
      labels:
        domain: k8s-gateway.nginx.org
    spec:
      gatewayClassName: nginx
      listeners:
      - name: http
        port: 80
        protocol: HTTP
    EOF
    ~~~

3. Finally, let's create the `HTTPRoute`:

    > **INFO**: This `HTTPRoute` uses the `Gateway` named `gateway` in this namespace, and will use the listener `http` to publish the route. The `Service` being exposed is the `reverse-words-blue` service on port `8080`.

    ~~~sh
    cat <<EOF | oc apply -f -
    apiVersion: gateway.networking.k8s.io/v1beta1
    kind: HTTPRoute
    metadata:
      name: reversewords
      namespace: reverse-words
    spec:
      parentRefs:
      - name: gateway
        sectionName: http
      hostnames:
      - reverse-words.apps.gateway-api.test.lab
      rules:
      - backendRefs:
        - name: reverse-words-blue
          port: 8080
    EOF
    ~~~

4. We can now access our application:

    ~~~sh
    curl http://reverse-words.apps.gateway-api.test.lab
    ~~~

    ~~~console
    Reverse Words Release: Blue. App version: v0.0.27
    ~~~

### Blue/Green Scenario

The goal in this scenario is having two versions of the same service and gradually routing traffic to the newer version.

**IMPORTANT**: This scenario relies on the application deployed on the previous section.

1. Deploy the new version of our application (`Green`)

    ~~~sh
    cat <<EOF | oc apply -f -
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: reverse-words-green
      namespace: reverse-words
      labels:
        app: reverse-words-green
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: reverse-words-green
      template:
        metadata:
          labels:
            app: reverse-words-green
        spec:
          containers:
          - name: reverse-words
            image: quay.io/mavazque/reversewords:0.28
            ports:
            - containerPort: 8080
              name: http
            env:
            - name: RELEASE
              value: "Green"
            livenessProbe:
              httpGet:
                path: /health
                port: 8080
              initialDelaySeconds: 5
              timeoutSeconds: 2
              periodSeconds: 15
            readinessProbe:
              httpGet:
                path: /health
                port: 8080
              initialDelaySeconds: 10
              timeoutSeconds: 2
              periodSeconds: 15
    ---
    apiVersion: v1
    kind: Service
    metadata:
      labels:
        app: reverse-words-green
      name: reverse-words-green
      namespace: reverse-words
    spec:
      ports:
      - port: 8080
        protocol: TCP
        targetPort: http
        name: http
      selector:
        app: reverse-words-green
      type: ClusterIP
    EOF
    ~~~

2. Delete the old `HTTPRoute` and create a new one with weights:

    ~~~sh
    oc -n reverse-words delete httproute reversewords
    ~~~

    > **NOTE**: Below route will send most of the request to the old service (`Blue`) and a few ones to the new one (`Green`).

    ~~~sh
    cat <<EOF | oc apply -f -
    apiVersion: gateway.networking.k8s.io/v1beta1
    kind: HTTPRoute
    metadata:
      name: reversewords
      namespace: reverse-words
    spec:
      parentRefs:
      - name: gateway
        sectionName: http
      hostnames:
      - reverse-words.apps.gateway-api.test.lab
      rules:
      - backendRefs:
        - name: reverse-words-blue
          port: 8080
          weight: 90
        - name: reverse-words-green
          port: 8080
          weight: 10
    EOF
    ~~~

3. If we try to access our application this is what we will get:

    ~~~sh
    for i in $(seq 1 10);do curl http://reverse-words.apps.gateway-api.test.lab; done
    ~~~

    ~~~console
    Reverse Words Release: Blue. App version: v0.0.27
    Reverse Words Release: Blue. App version: v0.0.27
    Reverse Words Release: Blue. App version: v0.0.27
    Reverse Words Release: Blue. App version: v0.0.27
    Reverse Words Release: Blue. App version: v0.0.27
    Reverse Words Release: Blue. App version: v0.0.27
    Reverse Words Release: Blue. App version: v0.0.27
    Reverse Words Release: Green. App version: v0.0.28
    Reverse Words Release: Blue. App version: v0.0.27
    Reverse Words Release: Blue. App version: v0.0.27   
    ~~~

4. We can update the weights, so traffic gets distributed evenly:

    ~~~sh
    oc -n reverse-words patch httproute reversewords -p '{"spec":{"rules":[{"backendRefs":[{"group":"","kind":"Service","name":"reverse-words-blue","port":8080,"weight":50},{"group":"","kind":"Service","name":"reverse-words-green","port":8080,"weight":50}],"matches":[{"path":{"type":"PathPrefix","value":"/"}}]}]}}' --type merge
    ~~~

5. And check the impact:

    ~~~sh
    for i in $(seq 1 10);do curl http://reverse-words.apps.gateway-api.test.lab; done
    ~~~

    ~~~console
    Reverse Words Release: Blue. App version: v0.0.27
    Reverse Words Release: Green. App version: v0.0.28
    Reverse Words Release: Blue. App version: v0.0.27
    Reverse Words Release: Blue. App version: v0.0.27
    Reverse Words Release: Blue. App version: v0.0.27
    Reverse Words Release: Blue. App version: v0.0.27
    Reverse Words Release: Green. App version: v0.0.28
    Reverse Words Release: Blue. App version: v0.0.27
    Reverse Words Release: Green. App version: v0.0.28
    Reverse Words Release: Green. App version: v0.0.28
    ~~~

6. We could remove the old service (`Blue`) from the balancing:

    ~~~sh
    oc -n reverse-words patch httproute reversewords -p '{"spec":{"rules":[{"backendRefs":[{"group":"","kind":"Service","name":"reverse-words-blue","port":8080,"weight":0},{"group":"","kind":"Service","name":"reverse-words-green","port":8080,"weight":100}],"matches":[{"path":{"type":"PathPrefix","value":"/"}}]}]}}' --type merge
    ~~~

    ~~~sh
    for i in $(seq 1 10);do curl http://reverse-words.apps.gateway-api.test.lab; done
    ~~~

    ~~~console
    Reverse Words Release: Green. App version: v0.0.28
    Reverse Words Release: Green. App version: v0.0.28
    Reverse Words Release: Green. App version: v0.0.28
    Reverse Words Release: Green. App version: v0.0.28
    Reverse Words Release: Green. App version: v0.0.28
    Reverse Words Release: Green. App version: v0.0.28
    Reverse Words Release: Green. App version: v0.0.28
    Reverse Words Release: Green. App version: v0.0.28
    Reverse Words Release: Green. App version: v0.0.28
    Reverse Words Release: Green. App version: v0.0.28
    ~~~

### Exposing a simple app via HTTPs

1. We need a TLS cert, let's generate a self-signed one:

    ~~~sh
    openssl req -new -newkey rsa:2048 -sha256 -days 3650 -nodes -x509 -extensions v3_ca -keyout /tmp/tls.key -out /tmp/tls.crt -subj "/C=ES/ST=Valencia/L=Valencia/O=IT/OU=IT/CN=*.apps.gateway-api.test.lab" -addext "subjectAltName = DNS:*.apps.gateway-api.test.lab"
    ~~~

2. The certificate needs to be stored in a secret:

    ~~~sh
    oc -n reverse-words create secret tls reversewords-gateway-tls --cert=/tmp/tls.crt --key=/tmp/tls.key
    ~~~

3. The `Gateway` needs to be updated, a new listener for https protocol will be created on port 443. This listener will be our tls terminator and will use the certificate we just created:

    ~~~sh
    cat <<EOF | oc apply -f -
    apiVersion: gateway.networking.k8s.io/v1beta1
    kind: Gateway
    metadata:
      name: gateway
      namespace: reverse-words
      labels:
        domain: k8s-gateway.nginx.org
    spec:
      gatewayClassName: nginx
      listeners:
      - name: http
        port: 80
        protocol: HTTP
      - name: https
        port: 443
        protocol: HTTPS
        tls:
          mode: Terminate
          certificateRefs:
          - kind: Secret
            name: reversewords-gateway-tls
            namespace: reverse-words
    EOF
    ~~~

4. Let's remove the old `HTTPRoute` and create a new one exposing the app via HTTPs:

    ~~~sh
    oc -n reverse-words delete httproute reversewords
    ~~~

    ~~~sh
    cat <<EOF | oc apply -f -
    apiVersion: gateway.networking.k8s.io/v1beta1
    kind: HTTPRoute
    metadata:
      name: reversewords
      namespace: reverse-words
    spec:
      parentRefs:
      - name: gateway
        sectionName: https
      hostnames:
      - reverse-words.apps.gateway-api.test.lab
      rules:
      - backendRefs:
        - name: reverse-words-green
          port: 8080
    EOF
    ~~~

5. We can now access our app via https:

    ~~~sh
    curl -k https://reverse-words.apps.gateway-api.test.lab
    ~~~~

    ~~~console
    Reverse Words Release: Green. App version: v0.0.28
    ~~~

6. If we try to access the app via http:

    ~~~sh
    curl http://reverse-words.apps.gateway-api.test.lab
    ~~~

    > **INFO**: Our `HTTPRoute` does not expose the app via http, this is expected.

    ~~~console
    <html>
    <head><title>404 Not Found</title></head>
    <body>
    <center><h1>404 Not Found</h1></center>
    <hr><center>nginx/1.23.4</center>
    </body>
    </html>
    ~~~

7. Usually you want to redirect users hitting the HTTP endpoint to the HTTPs endpoint, lets configure that:

    > **NOTE**: We need to create a new `HTTPRoute`, but if you take a closer look you will not see any backends being referenced, instead we are applying a `RequestRedirect` filter to tell the client to go look the HTTPs endpoint. More on filters [here](https://gateway-api.sigs.k8s.io/v1alpha2/guides/http-redirect-rewrite/).

    ~~~sh
    cat <<EOF | oc apply -f -
    apiVersion: gateway.networking.k8s.io/v1beta1
    kind: HTTPRoute
    metadata:
      name: reversewords-tls-redirect
      namespace: reverse-words
    spec:
      parentRefs:
      - name: gateway
        sectionName: http
      hostnames:
      - reverse-words.apps.gateway-api.test.lab
      rules:
      - filters:
        - type: RequestRedirect
          requestRedirect:
            scheme: https
            port: 443
    EOF
    ~~~

8. If we access the HTTP endpoint, we're told to go somewhere else:

    ~~~sh
    curl http://reverse-words.apps.gateway-api.test.lab
    ~~~

    ~~~console
    <html>
    <head><title>302 Found</title></head>
    <body>
    <center><h1>302 Found</h1></center>
    <hr><center>nginx/1.23.4</center>
    </body>
    </html>
    ~~~

9. If we tell `curl` to follow redirects (`-L`):

    ~~~sh
    curl -Lk http://reverse-words.apps.gateway-api.test.lab
    ~~~

    ~~~console
    Reverse Words Release: Green. App version: v0.0.28
    ~~~

## Useful Resources

* https://gateway-api.sigs.k8s.io/
* https://gateway-api.sigs.k8s.io/v1alpha2/guides/
* https://gateway-api.sigs.k8s.io/api-types/httproute/
* https://gateway-api.sigs.k8s.io/api-types/referencegrant/
* https://github.com/nginxinc/nginx-kubernetes-gateway/blob/main/docs/installation.md