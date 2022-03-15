# **Deploying an OpenShift Cluster with a TLS proxy using Assisted Installer**

This document briefly describes how to run a deployment of an OpenShift Cluster that uses a TLS proxy to access internet using Assisted Installer.

We will use [Assisted Installer CLI](https://github.com/karmab/aicli) in order to interact with the Assisted Service API from the CLI.

## **Preparing the TLS Proxy**

We will use a squid proxy with `ssl-bump` enabled. You can find the configuration file we used [here](https://github.com/mvazquezc/squid-container/blob/main/squid-tls.conf), the Containerfile to build a container image [here](https://github.com/mvazquezc/squid-container/blob/main/Containerfile-tls) and the script to start the proxy [here](https://github.com/mvazquezc/squid-container/blob/main/run-tls.sh).

## **Preparing the Deployment Files**

1. We will craft a parameters file that will be consumed by `aicli` to create our cluster:

    > :exclamation: Make sure to edit the `ignition_config_override` and the `additionalTrustBundle` with the CA that signed your squid proxy certificate. 

    ~~~yaml
    cluster: sno
    domain: e2e.bos.redhat.com
    network_type: OVNKubernetes
    sno: true
    openshift_version: 4.9.9
    pull_secret: pull_secret.json
    machine_network_cidr: 10.19.3.0/26
    proxy:
      http_proxy: http://10.19.3.4:3128
      https_proxy: http://10.19.3.4:3128
      no_proxy: 10.19.3.0/26
    ignition_config_override: '{"ignition": {"version": "3.1.0"}, "storage": {"files": [{"path": "/etc/pki/ca-trust/source/anchors/proxy-ca.pem", "mode": 420, "overwrite": true, "user": {"name": "root"}, "contents": {"source": "data:text/plain;base64,LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUR5VENDQXJHZ0F3SUJBZ0lVSHFXcEwwdWY5eHJHQXFDOGx6TjRNKzdBQUNZd0RRWUpLb1pJaHZjTkFRRUwKQlFBd2RERUxNQWtHQTFVRUJoTUNSVk14RVRBUEJnTlZCQWdNQ0ZaaGJHVnVZMmxoTVJFd0R3WURWUVFIREFoVwpZV3hsYm1OcFlURVhNQlVHQTFVRUNnd09VM0YxYVdRZ1UyVmpkWEpwZEhreEN6QUpCZ05WQkFzTUFrbFVNUmt3CkZ3WURWUVFEREJCemNYVnBaSEJ5YjNoNUxteHZZMkZzTUI0WERUSXlNRE13TWpBNU1UTXpNMW9YRFRNeU1ESXkKT0RBNU1UTXpNMW93ZERFTE1Ba0dBMVVFQmhNQ1JWTXhFVEFQQmdOVkJBZ01DRlpoYkdWdVkybGhNUkV3RHdZRApWUVFIREFoV1lXeGxibU5wWVRFWE1CVUdBMVVFQ2d3T1UzRjFhV1FnVTJWamRYSnBkSGt4Q3pBSkJnTlZCQXNNCkFrbFVNUmt3RndZRFZRUUREQkJ6Y1hWcFpIQnliM2g1TG14dlkyRnNNSUlCSWpBTkJna3Foa2lHOXcwQkFRRUYKQUFPQ0FROEFNSUlCQ2dLQ0FRRUFsSStBUWNUcUdGRnNPbktWWUU4OXNrbnB4SDdLZmJKcHNkY2k0ZVVkREtIYwpyUnVJdmJIRW1lZ2EyUUJRRkg2TURaM2MzMzdwNi9BVUlmMzgyREgxS0RtYkthMEhaSU1NV1hVeXhjWjdjLzhOClk4REVTT21kRmZpM2JlZVROeWJhOEQwVGhlNUJsVzJiK2tGeFRBcmlKY0prQk4vUStxcE84aDNjMUl2TkZOVCsKOFBhVk1OQ1dnNDEzcTA5Q3VOY0tZMEdzMFNQRytLTFpEVmN3a2pLTTVrL0hPdnZiM2J4Y3k1dG5OTzc4eEh4UQpkOG1idkUwUDBTMDRUVnZuTk9LOXY2SG8xcHNIVWMzMzRhdG9FUWdoWFl3b3RYUkF3ZnIyNmdISEVCbkVTaHh2CjJYL3BQVWhkZjZpREQ2dlJsM2xRYStDZmV6RmF0ME9vUHVVbmNFR3dXd0lEQVFBQm8xTXdVVEFkQmdOVkhRNEUKRmdRVXI4MThZblpmVVZ6Q1JaQW10TldnRjhkbXZnSXdId1lEVlIwakJCZ3dGb0FVcjgxOFluWmZVVnpDUlpBbQp0TldnRjhkbXZnSXdEd1lEVlIwVEFRSC9CQVV3QXdFQi96QU5CZ2txaGtpRzl3MEJBUXNGQUFPQ0FRRUFpYktqCktpbTZwbEYwQVl3RUROcTNlbFRoTWJXREFxMW90QmFqbkpiMDlqUDFOQm9mMVFBSG9WaHpKYmd1QWNnWkU2TGwKaUtBUGFNSVpHc2pHUVo2em9PeFFFL0F6N0FOczlqaGI1NHJwMDBubzNwdVkxL21ZaUxHVXlaNzY1bWFXNElhSApwNmV0Q3JMdHhSdFZsS2Z1bkxvSWsvcXZWeXNTQ3FkbXlNTGZRWUNZczUwSyszbUlmWFRuWVRSTlR0T3k1bnZaCm5YVS82L3Z3MGk5R0lhMlFPUGJ3Nys3bUxPeklldGo4YVJaZXhGa29PSVVMM0hrWlFLREVlVEdueW5RMWJlREgKVEdDOHRZR2I5dTBjaEpUaDZNZVFYSW5pb1lEQkNuOE8wZW4wODk0b0RnUXc4Ym9vakpFZlk0Umx6c1k4em9GOQpnWHJKZkRLSGdtUFFTSVNOU3c9PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tIAo="}}]}}'
    installConfig:
      additionalTrustBundle: |
        -----BEGIN CERTIFICATE-----
        MIIDyTCCArGgAwIBAgIUHqWpL0uf9xrGAqC8lzN4M+7AACYwDQYJKoZIhvcNAQEL
        BQAwdDELMAkGA1UEBhMCRVMxETAPBgNVBAgMCFZhbGVuY2lhMREwDwYDVQQHDAhW
        YWxlbmNpYTEXMBUGA1UECgwOU3F1aWQgU2VjdXJpdHkxCzAJBgNVBAsMAklUMRkw
        FwYDVQQDDBBzcXVpZHByb3h5LmxvY2FsMB4XDTIyMDMwMjA5MTMzM1oXDTMyMDIy
        ODA5MTMzM1owdDELMAkGA1UEBhMCRVMxETAPBgNVBAgMCFZhbGVuY2lhMREwDwYD
        VQQHDAhWYWxlbmNpYTEXMBUGA1UECgwOU3F1aWQgU2VjdXJpdHkxCzAJBgNVBAsM
        AklUMRkwFwYDVQQDDBBzcXVpZHByb3h5LmxvY2FsMIIBIjANBgkqhkiG9w0BAQEF
        AAOCAQ8AMIIBCgKCAQEAlI+AQcTqGFFsOnKVYE89sknpxH7KfbJpsdci4eUdDKHc
        rRuIvbHEmega2QBQFH6MDZ3c337p6/AUIf382DH1KDmbKa0HZIMMWXUyxcZ7c/8N
        Y8DESOmdFfi3beeTNyba8D0The5BlW2b+kFxTAriJcJkBN/Q+qpO8h3c1IvNFNT+
        8PaVMNCWg413q09CuNcKY0Gs0SPG+KLZDVcwkjKM5k/HOvvb3bxcy5tnNO78xHxQ
        d8mbvE0P0S04TVvnNOK9v6Ho1psHUc334atoEQghXYwotXRAwfr26gHHEBnEShxv
        2X/pPUhdf6iDD6vRl3lQa+CfezFat0OoPuUncEGwWwIDAQABo1MwUTAdBgNVHQ4E
        FgQUr818YnZfUVzCRZAmtNWgF8dmvgIwHwYDVR0jBBgwFoAUr818YnZfUVzCRZAm
        tNWgF8dmvgIwDwYDVR0TAQH/BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAibKj
        Kim6plF0AYwEDNq3elThMbWDAq1otBajnJb09jP1NBof1QAHoVhzJbguAcgZE6Ll
        iKAPaMIZGsjGQZ6zoOxQE/Az7ANs9jhb54rp00no3puY1/mYiLGUyZ765maW4IaH
        p6etCrLtxRtVlKfunLoIk/qvVysSCqdmyMLfQYCYs50K+3mIfXTnYTRNTtOy5nvZ
        nXU/6/vw0i9GIa2QOPbw7+7mLOzIetj8aRZexFkoOIUL3HkZQKDEeTGnynQ1beDH
        TGC8tYGb9u0chJTh6MeQXInioYDBCn8O0en0894oDgQw8boojJEfY4RlzsY8zoF9
        gXrJfDKHgmPQSISNSw==
        -----END CERTIFICATE-----
    ~~~

2. Next, we will create the extra manifest folder where we will store a MachineConfig that will configure our Proxy's CA in the server:

    > :exclamation: The file below is created as `manifests/99-proxy-ca.yaml`. We only have a master node (SNO), if you have worker nodes you need to duplicate this file and change the role, so it applies to workers.

    ~~~yaml
    apiVersion: machineconfiguration.openshift.io/v1
    kind: MachineConfig
    metadata:
      labels:
        machineconfiguration.openshift.io/role: master
      name: 99-proxy-ca
    spec:
      config:
        ignition:
          config: {}
          security:
            tls: {}
          timeouts: {}
          version: 3.1.0
        networkd: {}
        passwd: {}
        storage:
          files:
          - contents:
              source: data:text/plain;charset=utf-8;base64,LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUR5VENDQXJHZ0F3SUJBZ0lVSHFXcEwwdWY5eHJHQXFDOGx6TjRNKzdBQUNZd0RRWUpLb1pJaHZjTkFRRUwKQlFBd2RERUxNQWtHQTFVRUJoTUNSVk14RVRBUEJnTlZCQWdNQ0ZaaGJHVnVZMmxoTVJFd0R3WURWUVFIREFoVwpZV3hsYm1OcFlURVhNQlVHQTFVRUNnd09VM0YxYVdRZ1UyVmpkWEpwZEhreEN6QUpCZ05WQkFzTUFrbFVNUmt3CkZ3WURWUVFEREJCemNYVnBaSEJ5YjNoNUxteHZZMkZzTUI0WERUSXlNRE13TWpBNU1UTXpNMW9YRFRNeU1ESXkKT0RBNU1UTXpNMW93ZERFTE1Ba0dBMVVFQmhNQ1JWTXhFVEFQQmdOVkJBZ01DRlpoYkdWdVkybGhNUkV3RHdZRApWUVFIREFoV1lXeGxibU5wWVRFWE1CVUdBMVVFQ2d3T1UzRjFhV1FnVTJWamRYSnBkSGt4Q3pBSkJnTlZCQXNNCkFrbFVNUmt3RndZRFZRUUREQkJ6Y1hWcFpIQnliM2g1TG14dlkyRnNNSUlCSWpBTkJna3Foa2lHOXcwQkFRRUYKQUFPQ0FROEFNSUlCQ2dLQ0FRRUFsSStBUWNUcUdGRnNPbktWWUU4OXNrbnB4SDdLZmJKcHNkY2k0ZVVkREtIYwpyUnVJdmJIRW1lZ2EyUUJRRkg2TURaM2MzMzdwNi9BVUlmMzgyREgxS0RtYkthMEhaSU1NV1hVeXhjWjdjLzhOClk4REVTT21kRmZpM2JlZVROeWJhOEQwVGhlNUJsVzJiK2tGeFRBcmlKY0prQk4vUStxcE84aDNjMUl2TkZOVCsKOFBhVk1OQ1dnNDEzcTA5Q3VOY0tZMEdzMFNQRytLTFpEVmN3a2pLTTVrL0hPdnZiM2J4Y3k1dG5OTzc4eEh4UQpkOG1idkUwUDBTMDRUVnZuTk9LOXY2SG8xcHNIVWMzMzRhdG9FUWdoWFl3b3RYUkF3ZnIyNmdISEVCbkVTaHh2CjJYL3BQVWhkZjZpREQ2dlJsM2xRYStDZmV6RmF0ME9vUHVVbmNFR3dXd0lEQVFBQm8xTXdVVEFkQmdOVkhRNEUKRmdRVXI4MThZblpmVVZ6Q1JaQW10TldnRjhkbXZnSXdId1lEVlIwakJCZ3dGb0FVcjgxOFluWmZVVnpDUlpBbQp0TldnRjhkbXZnSXdEd1lEVlIwVEFRSC9CQVV3QXdFQi96QU5CZ2txaGtpRzl3MEJBUXNGQUFPQ0FRRUFpYktqCktpbTZwbEYwQVl3RUROcTNlbFRoTWJXREFxMW90QmFqbkpiMDlqUDFOQm9mMVFBSG9WaHpKYmd1QWNnWkU2TGwKaUtBUGFNSVpHc2pHUVo2em9PeFFFL0F6N0FOczlqaGI1NHJwMDBubzNwdVkxL21ZaUxHVXlaNzY1bWFXNElhSApwNmV0Q3JMdHhSdFZsS2Z1bkxvSWsvcXZWeXNTQ3FkbXlNTGZRWUNZczUwSyszbUlmWFRuWVRSTlR0T3k1bnZaCm5YVS82L3Z3MGk5R0lhMlFPUGJ3Nys3bUxPeklldGo4YVJaZXhGa29PSVVMM0hrWlFLREVlVEdueW5RMWJlREgKVEdDOHRZR2I5dTBjaEpUaDZNZVFYSW5pb1lEQkNuOE8wZW4wODk0b0RnUXc4Ym9vakpFZlk0Umx6c1k4em9GOQpnWHJKZkRLSGdtUFFTSVNOU3c9PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tIAo=
            mode: 420
            overwrite: true
            path: /etc/pki/ca-trust/source/anchors/proxy-ca.pem
      osImageURL: "" 
    ~~~

## **Running the Deployment** ##

1. Create the cluster:

    ~~~sh
    OFFLINE_TOKEN="my_token"
    # Create the cluster
    aicli --offlinetoken ${OFFLINE_TOKEN} create cluster --paramfile ./aicli_parameters.yml sno-cluster
    # Upload the extra manifests
    aicli create manifest --dir ./manifests sno-cluster
    ~~~

2. Download the discovery iso and boot the server with it:

    ~~~sh
    aicli download iso sno-cluster
    ~~~

3. Once the cluster is ready to install, start the installation:

    > :exclamation: You can check if the cluster is ready to install using `aicli list cluster` and checking the `Status`.

    ~~~sh
    aicli start cluster sno-cluster 
    ~~~
