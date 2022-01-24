# **ZTP Remote Worker Nodes at day 0 with Assisted Installer**

:warning: The work exposed here is not supported in any way by Red Hat, this is the result of exploratory work. Use at your own risk.

The information here asumes you have followed [this other document](../ztp-ai/README.md).

## **Requirements**

* OpenShift Cluster acting as Hub (We tested with 4.9.12)
* RH ACM (We tested with 2.4)
* Hardware with RedFish support (We virtualized hardware with KVM and emulated RedFish with SushyTools)
* OpenShift GitOps Operator deployed
* ZTP PolicyGenTool (We tested with v4.10)

## **Deployment**

We followed the [deployment steps](https://github.com/openshift-kni/cnf-features-deploy/blob/master/ztp/gitops-subscriptions/argocd/README.md) in the cnf-features-deploy repo as of commit [319460](https://github.com/openshift-kni/cnf-features-deploy/commit/319460602446063149c4266d3519195d080d5048).

1. Extract the required directories that will be used later for configuring the ZTP pipeline:

    > **NOTE**: We want to use ZTP PolicyGenTool v4.10, at the time of this writing there is no updated v4.10 tagged image, so we will be using `latest` tag. You can check tags [here](https://quay.io/repository/redhat_emp1/ztp-site-generator?tag=latest&tab=tags).
    
    ~~~sh
    podman pull quay.io/redhat_emp1/ztp-site-generator:latest
    mkdir -p ./out
    podman create -ti --name ztp-site-gen ztp-site-generator:latest bash
    podman cp ztp-site-gen:/home/ztp ./out
    podman rm -f ztp-site-gen
    ~~~
2. Three directories have been created:

    1. `argocd` -> We will use it to get the ArgoCD running on our Hub cluster configured
    2. `extra-manifests` -> Contain the source CRs files that SiteConfig use to generate extra manifest configMap. We won't be using this folder.
    3. `source-crs` -> Contain the source CRs files that PolicyGenTemplate use to generate the ACM policies. We won't be using this folder.
3. Patch the ArgoCD instance running on the hub

    > **NOTE**: Patch files are under `argocd` folder we extracted on the step above.
    ~~~sh
    # Patch the ArgoCD instance
    oc patch argocd openshift-gitops -n openshift-gitops --patch-file argocd/deployment/argocd-openshift-gitops-patch.json --type=merge
    # Patch the openshift-gitops-repo-server Deployment
    oc patch deployment openshift-gitops-repo-server -n openshift-gitops --patch-file argocd/deployment/deployment-openshift-repo-server-patch.json
    ~~~
4. Create the repo structure, you can use the [example folder](https://github.com/openshift-kni/cnf-features-deploy/tree/master/ztp/gitops-subscriptions/argocd/example) as inspiration. You can check the structure we created [here](./repo-structure) as well. You need to fill the details for your environments on the different files.
5. Access the Argo CD UI and add your git repository under `Settings -> Repositories`

    > **NOTE**: You can get the Argo CD UI URL using the command below:
    ~~~sh
    oc -n openshift-gitops get route openshift-gitops-server -o jsonpath='{.spec.host}'
    ~~~

    > **NOTE**: You can get the Admin's password using the command below:
    ~~~sh
     oc -n openshift-gitops get secret openshift-gitops-cluster -o jsonpath={'.data.admin\.password'} | base64 -d
    ~~~
6. Finally, edit the ArgoCD applications under the `argocd/deployment/` folder we extracted a few steps earlier:

    1. Update the URL to point to the git repo you configured in ArgoCD. The URL must end with .git.
    2. The `targetRevision` should indicate which branch to monitor.
    3. The `path` should specify the path to the SiteConfig or PolicyGenTemplate folders respectively.
    4. Example:
        
        **Sites**
        ~~~yaml
        path: ztp/remote-worker-day0/ztp-policygentool/repo-structure/site-configs/
        repoURL: https://github.com/RHsyseng/telco-operations.git
        targetRevision: main
        ~~~

        **Policies**
        ~~~yaml
        path: ztp/remote-worker-day0/ztp-policygentool/repo-structure/site-policies/
        repoURL: https://github.com/RHsyseng/telco-operations.git
        targetRevision: main
        ~~~
7. Before loading the applications, we need to apply the pre-reqs in the hub cluster, this will create the required namespaces and secrets for the BMHs and the installation:

    > **NOTE**: You can find an example of pre-reqs in this repo under `ztp/remote-worker-day0/ztp-policygentool/repo-structure/pre-reqs/` folder.
    ~~~sh
    oc apply -k pre-reqs/
    ~~~
8. Now we load the ArgoCD applications in the hub cluster:

    ~~~sh
    oc apply -k argocd/deployment/
    ~~~
9. The deployment of our ZTP cluster should start, we can monitor the progress using something like this:

    ~~~sh
    export CLUSTER=<clusterName>
    oc get agentclusterinstall -n $CLUSTER $CLUSTER -o jsonpath='{.status.conditions[?(@.type=="Completed")]}' | jq
    curl -sk $(oc get agentclusterinstall -n $CLUSTER $CLUSTER -o jsonpath='{.status.debugInfo.eventsURL}')  | jq '.[-2,-1]'
    ~~~