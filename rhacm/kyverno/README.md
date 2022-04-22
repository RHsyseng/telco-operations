# **Kyverno Policies on RHACM**

This is the result of an exploratory spike around using Kyverno vs RHACM Policies and what gaps exist between RHACM and Kyverno policy engines.

## **Deploying Kyverno**

As of today, Kyverno can be installed with Helm or from a yaml file. An operator is expected in the future.

> :exclamation: We will install latest 1.6 release (1.6.2 at the time of this writing).

~~~sh
oc apply -f https://raw.githubusercontent.com/kyverno/kyverno/release-1-6-2/config/install.yaml
~~~

We can also get the CLI tool:

~~~sh
curl -L https://github.com/kyverno/kyverno/releases/download/v1.6.2/kyverno-cli_v1.6.2_linux_x86_64.tar.gz -o /tmp/kyverno-cli_v1.6.2_linux_x86_64.tar.gz
sudo tar xvfz /tmp/kyverno-cli_v1.6.2_linux_x86_64.tar.gz -C /usr/local/bin/ kyverno
~~~

## **Kyverno Policies**

Kyverno policies consist of a collection of rules. Each rule has a `match` declaration, an optional exclude declaration, and one of a `validate`, `mutate`, `generate`, or `verifyImages` declaration. Each rule can contain only a single `validate`, `mutate`, `generate`, or `verifyImages` declaration.

### **Applying Kyverno Policies**

Policies can be applied in-cluster or outside the cluster. For cluster policies we have two types: `Policies` and `ClusterPolicies`:

* `Policies`: Apply to the namespace where they live.
* `ClusterPolicies`: Apply to all namespaces within the Cluster (there may be excluded namespaces like kube-system, etc. depending on the configuration of the webhook).

Outside the cluster we can use the [Kyverno CLI to do a dry-run](https://kyverno.io/docs/kyverno-cli/#apply) of our rules against a set of input resources.

One thing that you want to keep in mind is that before the validations happen, all the mutating rules across all policies will be executed first.

### **Kyverno Policies Configuration**

**Common Settings**

|Setting|Description|
|-------|-----------|
|validationFailureAction|What happens when the policy rule fails. Two settings `enforce` or `audit`. First one blocks the request, second one allows the request and audits the violation. Defaults to `audit`.|
|validationFailureActionOverrides| Allows to override the setting of `validationFailureAction` for specific namespaces.|
|background|If set to true (default setting), will check the rules against existing resources during a background scan.|
|schemaValidation|Will run schema validations for objects managed by the policy. Defaults to `true`.|
|failurePolicy|Defines what happens when the Kyverno webhook cannot be reached. Two settings `Ignore` or `Fail`. First one will block the requests, second one will allow the requests (note that those requests won't be mutated/validated). Defaults to `Fail`.|
|webhookTimeoutSeconds|Specifies the maximum time in seconds allowed to apply this policy. The default timeout is 10s. The value must be between 1 and 30 seconds.|

**Match/Exclude**

The `match` and `exclude` filters control which resources policies are applied to. They both share the same structure, and they can only contain one of the two elements:

|Clause|Description|
|------|-----------|
|any|Specifies resource filters on which Kyverno will perform the logical **OR** operation while choosing resources.|
|all|Specifies resource filters on which Kyverno will perform the logical **AND** operation while choosing resources.|

The following filters can be used:

|Filter|Description|
|------|-----------|
|resources|Select resources by names, namespaces, kinds, label selectors, annotations, and namespace selectors.|
|subjects|Select users, user groups, and service accounts.|
|roles|Select namespaced roles.|
|clusterRoles|Select cluster wide roles.|

More information about `match statements` can be found [here](https://kyverno.io/docs/writing-policies/match-exclude/#match-statements).

### **Writing Policies**

You can find information about writing Kyverno policies [here](https://kyverno.io/docs/writing-policies/).

The Kyverno community has some pre-defined policies on the project site that can be used right away. You can find them [here](https://kyverno.io/policies).

## **Policies Created as part of the Spike**

|Policy Name|Policy Type|Description|Link|
|-----------|-----------|-----------|----|
|`team-validate-ns-schema`|Validate|When a namespace or project request is created. It applies to platform team admins or service accounts from argo. The namespace should be named: $platform-$team.| [v1](./assets/team-validate-ns-schema.yaml), [v2](./assets/team-validate-ns-schema-noloop.yaml)|
|`team-generate-argocd-permissions`|Generate|When a namespace is created. It creates rolebindings in order to use argocd.| [v1](./assets/generate-argocd-permissions.yaml)|
|`team-mutate-resource-labels`|Mutate|Whenever a namespaced object is created, it needs to get the following labels: owner.example.com/team, team.example.com/team.|[v1](./assets/team-mutate-resource-labels.yaml)
|`team-approve-subscriptions`|Mutate|Whenever a subscription is created by a member in team1, the approval strategy will be set to automatic.|[v1](./assets/autoapprove-team1-subscriptions.yaml)|
|`approve-installplan`|Mutate|Whenever a installplan is created in the namespace where the policy exist, it will be approved automatically. Inspired by [this issue](https://github.com/stolostron/policy-collection/issues/256).|[v1](./assets/autoapprove-installplans-in-namespace.yaml)|

## Current gaps in ACM vs Kyverno

* Deleting the policy doesn't delete the content.
* No way to have policies that rely on webhooks (validate, mutate).
* No way to have policies that create resources out of an event (like a namespace creation).
* We could templatize kyverno policies using the [policy-generator-plugin](https://github.com/stolostron/policy-generator-plugin)

## Concerns

* Depending on the scope of the policies, it's pretty easy to overwhelm the kyverno webhook server and lose access to the cluster's API. It seems this is a known issue.

    ~~~sh
    oc delete validatingwebhookconfiguration.admissionregistration.k8s.io/kyverno-policy-validating-webhook-cfg validatingwebhookconfiguration.admissionregistration.k8s.io/kyverno-resource-validating-webhook-cfg; oc delete mutatingwebhookconfiguration.admissionregistration.k8s.io/kyverno-policy-mutating-webhook-cfg mutatingwebhookconfiguration.admissionregistration.k8s.io/kyverno-verify-mutating-webhook-cfg mutatingwebhookconfiguration.admissionregistration.k8s.io/kyverno-resource-mutating-webhook-cfg

    oc -n kyverno delete pod -l app=kyverno
    ~~~

## Upstream contributions as part of the Spike

* [PR 3558](https://github.com/kyverno/kyverno/pull/3558) that fixes [3555](https://github.com/kyverno/kyverno/issues/3555).
* [PR 299](https://github.com/kyverno/policies/pull/299) that contributes the namespace name validation to the OpenShift policies group.
