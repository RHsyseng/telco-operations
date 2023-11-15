# OpenShift Secrets Store CSI Driver with Vault

This was a test to understand how Secrets Store CSI Driver can be leveraged when having an external secret provider like Vault.

Versions used were OpenShift 4.14.2 and Secrets Store CSI Driver Operator 4.14.0-202310201027.

1. [Get a Vault server up and running](https://linuxera.org/running-vault-on-podman/)

2. Deploy the OpenShift Secrets Store CSI Driver.

    ~~~sh
    cat <<EOF | oc apply -f -
    apiVersion: operators.coreos.com/v1alpha1
    kind: Subscription
    metadata:
      name: secrets-store-csi-driver-operator
      namespace: openshift-cluster-csi-drivers
    spec:
      channel: "preview"
      name: secrets-store-csi-driver-operator
      source: redhat-operators
      sourceNamespace: openshift-marketplace
    EOF
    ~~~

3. Create a `ClusterCSIDriver`.

    ~~~sh
    cat <<EOF | oc apply -f -
    apiVersion: operator.openshift.io/v1
    kind: ClusterCSIDriver
    metadata:
        name: secrets-store.csi.k8s.io
    spec:
      managementState: Managed
    EOF
    ~~~

4. Privileged SCC is required for the provider to work.

    ~~~sh
    oc -n openshift-cluster-csi-drivers adm policy add-scc-to-user privileged -z vault-csi-provider
    ~~~

5. Deploy the Vault CSI Provider.

    >**NOTE**: Based on this [file-commit](https://github.com/hashicorp/vault-csi-provider/blob/9b869b74823bb9c39b513503d96c4f893018f18e/deployment/vault-csi-provider.yaml). Added `privileged: true` to the securityContext of the container.

    ~~~sh
    cat <<EOF | oc apply -f -
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: vault-csi-provider
      namespace: openshift-cluster-csi-drivers
    ---
    apiVersion: rbac.authorization.k8s.io/v1
    kind: ClusterRole
    metadata:
      name: vault-csi-provider-clusterrole
    rules:
    - apiGroups:
      - ""
      resources:
      - serviceaccounts/token
      verbs:
      - create
    ---
    apiVersion: rbac.authorization.k8s.io/v1
    kind: ClusterRoleBinding
    metadata:
      name: vault-csi-provider-clusterrolebinding
    roleRef:
      apiGroup: rbac.authorization.k8s.io
      kind: ClusterRole
      name: vault-csi-provider-clusterrole
    subjects:
    - kind: ServiceAccount
      name: vault-csi-provider
      namespace: openshift-cluster-csi-drivers
    ---
    apiVersion: rbac.authorization.k8s.io/v1
    kind: Role
    metadata:
      name: vault-csi-provider-role
      namespace: openshift-cluster-csi-drivers
    rules:
    - apiGroups: [""]
      resources: ["secrets"]
      verbs: ["get"]
      resourceNames:
      - vault-csi-provider-hmac-key
    # 'create' permissions cannot be restricted by resource name:
    # https://kubernetes.io/docs/reference/access-authn-authz/rbac/#referring-to-resources
    - apiGroups: [""]
      resources: ["secrets"]
      verbs: ["create"]
    ---
    apiVersion: rbac.authorization.k8s.io/v1
    kind: RoleBinding
    metadata:
      name: vault-csi-provider-rolebinding
      namespace: openshift-cluster-csi-drivers
    roleRef:
      apiGroup: rbac.authorization.k8s.io
      kind: Role
      name: vault-csi-provider-role
    subjects:
    - kind: ServiceAccount
      name: vault-csi-provider
      namespace: openshift-cluster-csi-drivers
    ---
    apiVersion: apps/v1
    kind: DaemonSet
    metadata:
      labels:
        app.kubernetes.io/name: vault-csi-provider
      name: vault-csi-provider
      namespace: openshift-cluster-csi-drivers
    spec:
      updateStrategy:
        type: RollingUpdate
      selector:
        matchLabels:
          app.kubernetes.io/name: vault-csi-provider
      template:
        metadata:
          labels:
            app.kubernetes.io/name: vault-csi-provider
        spec:
          serviceAccountName: vault-csi-provider
          tolerations:
          containers:
            - name: provider-vault-installer
              image: docker.io/hashicorp/vault-csi-provider:1.4.1
              securityContext:
                privileged: true
              imagePullPolicy: Always
              args:
                - -endpoint=/provider/vault.sock
                - -debug=false
              resources:
                requests:
                  cpu: 50m
                  memory: 100Mi
                limits:
                  cpu: 50m
                  memory: 100Mi
              volumeMounts:
                - name: providervol
                  mountPath: "/provider"
              livenessProbe:
                httpGet:
                  path: "/health/ready"
                  port: 8080
                  scheme: "HTTP"
                failureThreshold: 2
                initialDelaySeconds: 5
                periodSeconds: 5
                successThreshold: 1
                timeoutSeconds: 3
              readinessProbe:
                httpGet:
                  path: "/health/ready"
                  port: 8080
                  scheme: "HTTP"
                failureThreshold: 2
                initialDelaySeconds: 5
                periodSeconds: 5
                successThreshold: 1
                timeoutSeconds: 3
          volumes:
            - name: providervol
              hostPath:
                path: "/etc/kubernetes/secrets-store-csi-providers"
          nodeSelector:
            kubernetes.io/os: linux
    EOF
    ~~~

6. Create a secret in Vault.

    ~~~sh
    vault kv put -mount=kv team1/db-pass password="mys3cretdbp4ss"
    ~~~

7. Verify secret is readable.

    ~~~sh
    vault kv get -mount=kv team1/db-pass

    ==== Secret Path ====
    kv/data/team1/db-pass

    ======= Metadata =======
    Key                Value
    ---                -----
    created_time       2023-11-15T08:34:51.014161533Z
    custom_metadata    <nil>
    deletion_time      n/a
    destroyed          false
    version            1

    ====== Data ======
    Key         Value
    ---         -----
    password    mys3cretdbp4ss
    ~~~

8. Create the required configurations in Kubernetes to integrate with Vault.

    > **NOTE**: I'm using a long-lived SA token here, this is against the recommendation of using short-lived tokens. For production use, you must either run Vault on Kubernetes and use in-cluster auth or use the [JWT OIDC provider for Kubernetes](https://developer.hashicorp.com/vault/docs/auth/jwt/oidc-providers/kubernetes).

    ~~~sh
    oc apply -f - <<EOF
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: vault
      namespace: openshift-cluster-csi-drivers
    ---
    apiVersion: v1
    kind: Secret
    metadata:
      name: vault-k8s-auth-secret
      namespace: openshift-cluster-csi-drivers
      annotations:
        kubernetes.io/service-account.name: vault
    type: kubernetes.io/service-account-token
    ---
    apiVersion: rbac.authorization.k8s.io/v1
    kind: ClusterRoleBinding
    metadata:
      name: vault-sa-tokenreview-binding
    roleRef:
      apiGroup: rbac.authorization.k8s.io
      kind: ClusterRole
      name: system:auth-delegator
    subjects:
      - kind: ServiceAccount
        name: vault
        namespace: openshift-cluster-csi-drivers
    EOF
    ~~~

9. Get Kubernetes required information.

    ~~~sh
    KUBERNETES_API=$(oc whoami --show-server)
    VAULT_SA_JWT=$(oc -n openshift-cluster-csi-drivers get secret vault-k8s-auth-secret -o jsonpath='{.data.token}' | base64 -d)
    KUBERNETES_API_IP_PORT=$(echo $KUBERNETES_API | awk -F "//" '{print $2}')
    KUBERNETES_API_CA=$(openssl s_client -connect $KUBERNETES_API_IP_PORT </dev/null 2>/dev/null | openssl x509 -outform PEM)
    ~~~

10. Configure [Kubernetes authentication](https://developer.hashicorp.com/vault/docs/auth/kubernetes) in Vault.

    ~~~sh
    vault auth enable kubernetes
    vault write auth/kubernetes/config kubernetes_host="$KUBERNETES_API" token_reviewer_jwt="$VAULT_SA_JWT" kubernetes_ca_cert="$KUBERNETES_API_CA"
    ~~~

11. Create a Vault policy and add a user to the Kubernetes auth so the app that we will deploy later can read the secret we just created.

    > **NOTE**: For the user we're using db-app-sa ServiceAccountName and db-app Namespace.

    ~~~sh
    # Policy
    vault policy write database-app - <<EOF
    path "kv/data/team1/db-pass" {
      capabilities = ["read"]
    }
    EOF
    # User
    vault write auth/kubernetes/role/database bound_service_account_names=db-app-sa bound_service_account_namespaces=db-app policies=database-app ttl=20m
    ~~~

12. Create the namespace for our application.

    ~~~sh
    oc create namespace db-app
    ~~~

13. Define a `SecretProviderClass` for our Vault store.

    > **NOTE**: Update the `vaultAddress` to match your environment. We're not validating TLS certs, you can use the different parameters to specify CA so TLS verification is not skipped.

    ~~~sh
    cat <<EOF | oc apply -f -
    apiVersion: secrets-store.csi.x-k8s.io/v1
    kind: SecretProviderClass
    metadata:
      name: vault-database
      namespace: db-app
    spec:
      provider: vault
      parameters:
        vaultAddress: "https://10.19.3.5:8201"
        vaultSkipTLSVerify: "true"
        roleName: "database"
        objects: |
          - objectName: "db-password"
            secretPath: "kv/data/team1/db-pass"
            secretKey: "password"
    EOF
    ~~~

14. Create the application consuming the secret.

    ~~~sh
    cat <<EOF | oc apply -f -
    apiVersion: v1
    kind: ServiceAccount
    metadata:
      name: db-app-sa
      namespace: db-app
    ---
    kind: Pod
    apiVersion: v1
    metadata:
      name: dbapp
      namespace: db-app
    spec:
      serviceAccountName: db-app-sa
      containers:
      - image: quay.io/mavazque/trbsht:latest
        name: dbapp
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          seccompProfile:
            type: RuntimeDefault
          capabilities:
            drop:
              - ALL
        volumeMounts:
        - name: secrets-store-inline
          mountPath: "/mnt/secrets-store"
          readOnly: true
      volumes:
        - name: secrets-store-inline
          csi:
            driver: secrets-store.csi.k8s.io
            readOnly: true
            volumeAttributes:
              secretProviderClass: "vault-database"
    EOF
    ~~~

15. We can access the pod and see the secret.

    ~~~sh
    oc -n db-app exec -ti dbapp -- cat /mnt/secrets-store/db-password

    mys3cretdbp4ss
    ~~~

16. We can also sync vault data into a Kubernetes Secret, so our pod can consume it that way. When a pod references this SecretProviderClass, the CSI driver will create a Kubernetes Secret called "db-pass" with the "password" field set to the contents of the "db-password" object from the parameters. In this case, the pod will wait for the secret to be created before starting, and the secret will be deleted when all pods using this SecretProviderClass are stopped.

17. Update the SecretProviderClass to include the `secretObjects` entry.

    > **NOTE**: List of supported secret types can be found [here](https://secrets-store-csi-driver.sigs.k8s.io/topics/sync-as-kubernetes-secret.html).

    ~~~sh
    cat <<EOF | oc apply -f -
    apiVersion: secrets-store.csi.x-k8s.io/v1
    kind: SecretProviderClass
    metadata:
      name: vault-database
      namespace: db-app
    spec:
      provider: vault
      secretObjects:
        - data:
          - key: password
            objectName: db-password
          secretName: db-pass
          type: Opaque
      parameters:
        vaultAddress: "https://10.19.3.5:8201"
        vaultSkipTLSVerify: "true"
        roleName: "database"
        objects: |
          - objectName: "db-password"
            secretPath: "kv/data/team1/db-pass"
            secretKey: "password"
    EOF
    ~~~

18. If we try to get the secret, it won't be created.

    ~~~sh
    oc -n db-app get secret db-pass

    Error from server (NotFound): secrets "db-pass" not found
    ~~~

19. If we create a pod requesting such secret via the SecretProviderClass, we will see that the secret gets created.

    ~~~sh
    cat <<EOF | oc apply -f -
    kind: Pod
    apiVersion: v1
    metadata:
      name: dbapp-secret
      namespace: db-app
    spec:
      serviceAccountName: db-app-sa
      containers:
      - image: quay.io/mavazque/trbsht:latest
        name: dbapp
        env:
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-pass
              key: password
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          seccompProfile:
            type: RuntimeDefault
          capabilities:
            drop:
              - ALL
        volumeMounts:
        - name: secrets-store-inline
          mountPath: "/mnt/secrets-store"
          readOnly: true
      volumes:
        - name: secrets-store-inline
          csi:
            driver: secrets-store.csi.k8s.io
            readOnly: true
            volumeAttributes:
              secretProviderClass: "vault-database"
    EOF
    ~~~

20. Get secret.

    ~~~sh
    oc -n db-app get secret db-pass

    NAME      TYPE     DATA   AGE
    db-pass   Opaque   1      22s
    ~~~

21. Check env var.

    ~~~sh
    oc -n db-app exec -ti dbapp-secret -- sh -c 'echo $DB_PASSWORD'

    mys3cretdbp4ss
    ~~~

22. If we delete **every** pod using the SecretProviderClass, the secret will be gone as well.

    ~~~sh
    oc -n db-app delete pod dbapp-secret db-app
    oc -n db-app get secret db-pass

    Error from server (NotFound): secrets "db-pass" not found
    ~~~

## Resources
- [https://docs.openshift.com/container-platform/4.14/storage/container_storage_interface/persistent-storage-csi-secrets-store.html](https://docs.openshift.com/container-platform/4.14/storage/container_storage_interface/persistent-storage-csi-secrets-store.html)
- [https://docs.openshift.com/container-platform/4.14/nodes/pods/nodes-pods-secrets-store.html#mounting-secrets-external-secrets-store](https://docs.openshift.com/container-platform/4.14/nodes/pods/nodes-pods-secrets-store.html#mounting-secrets-external-secrets-store)
- [https://cloud.redhat.com/blog/introducing-the-secret-store-csi-driver-in-openshift](https://cloud.redhat.com/blog/introducing-the-secret-store-csi-driver-in-openshift)
- [https://developer.hashicorp.com/vault/tutorials/kubernetes/kubernetes-secret-store-driver](https://developer.hashicorp.com/vault/tutorials/kubernetes/kubernetes-secret-store-driver)
- [https://developer.hashicorp.com/vault/docs/auth/kubernetes](https://developer.hashicorp.com/vault/docs/auth/kubernetes)
- [https://github.com/hashicorp/vault-csi-provider/](https://github.com/hashicorp/vault-csi-provider/)
- [https://secrets-store-csi-driver.sigs.k8s.io/introduction](https://secrets-store-csi-driver.sigs.k8s.io/introduction)
