# OpenShift Cluster Logging with the Loki Stack

This doc covers how to deploy the OpenShift Cluster Logging using Vector as the collector and Loki as the log store.

Information in this document is not supported by Red Hat, official docs can be found [here](https://docs.openshift.com/container-platform/4.12/logging/cluster-logging-loki.html).

Versions used:

- OpenShift v4.12
- Cluster Logging Operator v5.6.3
- Loki Operator v5.6.3

The end goal is to be able to create alerts from the logs ingested by Loki.

## Required Operators Deployment

Two operators are required, on one hand the Cluster Logging Operator will manage the Cluster Logging subsystem while on the other hand the Loki Operator will manage the Loki subsystem.

All the commands executed below must be run connected to the OpenShift cluster as cluster-admin.

> **NOTE**: We will be deploying the operators from the command line, you can do the same from the OpenShift Web Console.

1. Create the required `Namespaces`:

    ~~~sh
    cat << EOF | oc apply -f -
    ---
    apiVersion: v1
    kind: Namespace
    metadata:
      labels:
        kubernetes.io/metadata.name: openshift-operators-redhat
        openshift.io/cluster-monitoring: "true"
      name: openshift-operators-redhat
    ---
    apiVersion: v1
    kind: Namespace
    metadata:
      labels:
        kubernetes.io/metadata.name: openshift-logging
        openshift.io/cluster-monitoring: "true"
      name: openshift-logging
    EOF
    ~~~

2. Create the required `OperatorGroups`:

    ~~~sh
    cat << EOF | oc apply -f -
    ---
    apiVersion: operators.coreos.com/v1
    kind: OperatorGroup
    metadata:
      nme: openshift-operators-redhat
      namespace: openshift-operators-redhat
    spec:
      upgradeStrategy: Default
    ---
    apiVersion: operators.coreos.com/v1
    kind: OperatorGroup
    metadata:
      name: openshift-logging
      namespace: openshift-logging
    spec:
      targetNamespaces:
      - openshift-logging
      upgradeStrategy: Default
    EOF
    ~~~

3. Create the required `Subscriptions`:

    ~~~sh
    cat << EOF | oc apply -f -
    ---
    apiVersion: operators.coreos.com/v1alpha1
    kind: Subscription
    metadata:
      name: loki-operator
      namespace: openshift-operators-redhat
    spec:
      channel: stable
      installPlanApproval: Automatic
      name: loki-operator
      source: redhat-operators
      sourceNamespace: openshift-marketplace
      startingCSV: loki-operator.v5.6.3
    ---
    apiVersion: operators.coreos.com/v1alpha1
    kind: Subscription
    metadata:
      name: cluster-logging
      namespace: openshift-logging
    spec:
      channel: stable-5.6
      installPlanApproval: Automatic
      name: cluster-logging
      source: redhat-operators
      sourceNamespace: openshift-marketplace
      startingCSV: cluster-logging.v5.6.3
    EOF
    ~~~

## Deploying the Loki stack

Once we have the required operators running, we can go ahead and deploy the Loki subsystem.

1. Loki requires an S3 bucket, we need to provide the credentials for Loki to access it:

    > **NOTE**: In our case we're using a self-hosted S3 server, so we need to provide the CA information as well.

    ~~~sh
    ---
    cat << EOF | oc apply -f -
    apiVersion: v1
    kind: Secret
    metadata:
      name: logging-loki-s3
      namespace: openshift-logging
    stringData:
      access_key_id: <redacted>
      access_key_secret: <redacted>
      bucketnames: loki-storage
      endpoint: https://s3-server.example.com:9002
      region: eu-central-1
    ---
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: s3-storage-cert
      namespace: openshift-logging
    data:
      ca.pem: |
        -----BEGIN CERTIFICATE-----
        MIIEFzCCAv+gAwIBAgIUSUnRjrxnl7C15oyLHz7e+XzDNTwwDQYJKoZIhvcNAQEL
        .
        .
        .
        uAguTlH9VVsEf5sAYpg+jkXv/wjVpYPSiGwLbG8Wo3qi8ipSBZ32nLr9pg==
        -----END CERTIFICATE-----
    EOF
    ~~~

2. Create the `LokiStack`:

    > **NOTE**: If we look at the configuration you can see different retention configs can be used. Note that we are using the `1x.extra-small` size which is **not** supported (it's meant for demos, like this one).

    ~~~sh
    cat << EOF | oc apply -f -
    ---
    apiVersion: loki.grafana.com/v1
    kind: LokiStack
    metadata:
      name: logging-loki
      namespace: openshift-logging
    spec:
      limits:
        global: 
          retention: 
            days: 5
            streams:
            - days: 2
              priority: 1
              selector: '{kubernetes_namespace_name=~"test.+"}' 
            - days: 5
              priority: 1
              selector: '{log_type="infrastructure"}'
      managementState: Managed
      replicationFactor: 1
      # https://docs.openshift.com/container-platform/4.12/logging/cluster-logging-loki.html#deployment-sizing_cluster-logging-loki
      size: 1x.extra-small
      storage:
        schemas:
        - effectiveDate: "2022-06-01"
          version: v12
        secret:
          name: logging-loki-s3
          type: s3
        tls:
          caName: s3-storage-cert
          caKey: ca.pem
      storageClassName: lvms-vg1
      tenants:
        mode: openshift-logging
      rules:
        enabled: true
        selector:
          matchLabels:
            openshift.io/cluster-monitoring: "true"
        namespaceSelector:
          matchLabels:
            openshift.io/cluster-monitoring: "true"
    EOF
    ~~~

## Configure the OpenShift Cluster Logging subsystem

Now that Loki is up and running, we can go ahead and configure OpenShift to store logs on it. We will use the `ClusterLogging` resource in order to configure that.

1. Now we can create the `ClusterLogging`:

    > **NOTE**: We just set the collector to Vector and pointed to our LokiStack instance as our log store.

    ~~~sh
    cat << EOF | oc apply -f -
    apiVersion: logging.openshift.io/v1
    kind: ClusterLogging
    metadata:
      name: instance
      namespace: openshift-logging
    spec:
      managementState: Managed
      logStore:
        type: lokistack
        lokistack:
          name: logging-loki
      collection:
        type: vector
    EOF
    ~~~

At this point we should have started getting our logs stored in Loki, we can access the OpenShift Web Console and under `Observe` we should find a `Logs` section.

![OpenShift Web Console Logs](./assets/ocp_console_logs.png)

We can choose the time period (Num 1) and between three different streams (Num 2):

1. `Application`: Logs from user workloads.
2. `Infrastructure`: Logs from the platform.
3. `Audit`: Logs from the Kubernetes auditing subsystem.

### Audit logs

Audit logs are not sent to the logging subsystem by default, in order to enable audit log collection you need to explicitly configure it:

1. Forward all logs to the default log store (Loki):

    > **NOTE**: You must specify all three types of logs in the pipeline: application, infrastructure, and audit. If you do not specify a log type, those logs are not stored and will be lost.

    > **NOTE2**: The internal Loki log store does not provide secure storage for audit logs. Verify that the system to which you forward audit logs complies with your organizational and governmental regulations and is properly secured. The logging subsystem for Red Hat OpenShift does not comply with those regulations.

    ~~~sh
    cat << EOF | oc apply -f -
    apiVersion: logging.openshift.io/v1
    kind: ClusterLogForwarder
    metadata:
      name: instance
      namespace: openshift-logging
    spec:
      pipelines: 
      - name: all-to-default
        inputRefs:
        - infrastructure
        - application
        - audit
        outputRefs:
        - default
    EOF
    ~~~

2. At this point you should see audit logs on the UI.

## Creating Alerts out of our logs

At this point we have the logging subsystem ingesting our logs, next step will be configuring alerts out of them.

1. We need to tell Loki how to connect to the Alertmanager deployed in the OpenShift cluster, we will use a `RulerConfig` for that:

    ~~~sh
    cat << EOF | oc apply -f -
    ---
    apiVersion: loki.grafana.com/v1beta1
    kind: RulerConfig
    metadata:
      name: rulerconfig
      namespace: openshift-logging
    spec:
      evaluationInterval: 1m
      pollInterval: 1m
      alertmanager:
        discovery:
          enableSRV: true
          refreshInterval: 1m
        enableV2: true
        endpoints:
          - "https://_web._tcp.alertmanager-operated.openshift-monitoring.svc"
        enabled: true
        refreshPeriod: 10s 
    EOF
    ~~~

At this point we are ready to create alerts, we can create two kinds of alerting rules:

1. `AlertingRule`: Alerting rules allow you to define alert conditions based on Prometheus expression language expressions and to send notifications about firing alerts to an external service.
2. `RecordingRule`: Recording rules allow you to precompute frequently needed or computationally expensive expressions and save their result as a new set of time series.

Let's add an `AlertingRule`:

~~~sh
cat << EOF | oc apply -f -
---
apiVersion: loki.grafana.com/v1beta1
kind: AlertingRule
metadata:
  name: loki-operator-infra-alerts
  namespace: openshift-operators-redhat
  labels:
    openshift.io/cluster-monitoring: "true"
spec:
  tenantID: "infrastructure"
  groups:
    - name: LokiOperatorHighReconciliationError
      rules:
        - alert: HighPercentageError
          expr: |
            sum(rate({kubernetes_namespace_name="openshift-operators-redhat", kubernetes_pod_name=~"loki-operator-controller-manager.*"} |= "error" [1m])) by (job)
              /
            sum(rate({kubernetes_namespace_name="openshift-operators-redhat", kubernetes_pod_name=~"loki-operator-controller-manager.*"}[1m])) by (job)
              > 0.01
          for: 10s
          labels:
            severity: page
            tenantId: infrastructure
          annotations:
            summary: High Loki Operator Reconciliation Errors
EOF
~~~