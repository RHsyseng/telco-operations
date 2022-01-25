# **Block workloads adding tolerations for master taints**

The work here is heavily based on the resources exposed by Karen Bruner in these blog posts:

* [Better Kubernetes Security with Open Policy Agent (OPA) - Part 1](https://cloud.redhat.com/blog/better-kubernetes-security-with-open-policy-agent-opa-part-1)
* [Better Kubernetes Security with Open Policy Agent (OPA) - Part 2](https://cloud.redhat.com/blog/better-kubernetes-security-with-open-policy-agent-opa-part-2)

This work tries to answer the questions exposed in [this card](https://issues.redhat.com/browse/KNIP-1816).

## **Requirements**

* OpenShift Cluster (We tested with 4.9.12)
* OpenPolicyAgent Gatekeeper deployed on the cluster (We tested with CSV gatekeeper-operator-product.v0.2.1)

## **Policy**

Inside the [assets/no-master-toleration/](./assets/no-master-toleration/) folder we have the `rego` policy and the tests files. You can run the tests as follows:

> **NOTE**: You can download the opa cli from [https://github.com/open-policy-agent/opa/releases](https://github.com/open-policy-agent/opa/releases).

~~~sh
opa test --explain fails src.rego src_test.rego

data.restrictedtainttoleration.test_input_no_global_violation: PASS (544.483µs)
data.restrictedtainttoleration.test_input_ok_global_allow: PASS (363.567µs)
data.restrictedtainttoleration.test_input_no_global_equal_match_violation: PASS (401.24µs)
data.restrictedtainttoleration.test_input_ok_global_equal_match_allow: PASS (357.066µs)
data.restrictedtainttoleration.test_input_equal_match_violation: PASS (625.204µs)
data.restrictedtainttoleration.test_input_equal_no_effect_match_violation: PASS (565.071µs)
data.restrictedtainttoleration.test_input_equal_no_operator_match_violation: PASS (576.912µs)
data.restrictedtainttoleration.test_input_equal_no_effect_no_operator_match_violation: PASS (594.109µs)
data.restrictedtainttoleration.test_input_equal_different_value_match_allow: PASS (1.448449ms)
data.restrictedtainttoleration.test_input_no_toleration_field_allow: PASS (396.695µs)
--------------------------------------------------------------------------------
PASS: 10/10
~~~

There is a gatekeeper policies library where there are existing policies written by the community, you can also use the rego playground to tests your policies, links below:

* [GateKeeper Library](https://github.com/open-policy-agent/gatekeeper-library/)
* [Rego Playground](https://play.openpolicyagent.org/)

## **Enforcing Policy on OpenShift/Kubernetes**

Inside the [assets/no-master-toleration/k8s/](./assets/no-master-toleration/k8s/) folder we have the `ConstraintTemplate` file and the `Constraint` file.

1. First, we need to load the `ConstraintTemplate`:

    ~~~sh
    oc create -f assets/no-master-toleration/k8s/constraint_template.yaml
    ~~~

2. Second, we can create a `Constraint` out of the `ConstraintTemplate` we just created:

    ~~~sh
    oc create -f assets/no-master-toleration/k8s/constraint.yaml
    ~~~

3. If we look inside the `Constraint` file we will see a list of namespaces where these constraints will **not** be enforced, as of the time of this writing (01/25/2022) the `excludedNamespaces` clause does not support prefix matching, you can see the enhancement request [here](https://github.com/open-policy-agent/gatekeeper/issues/500).

## **Testing the Policy on OpenShift/Kubernetes**

At this point we already have the `Constraint` loaded, so we can use the pod files in the [assets/no-master-toleration/k8s/](./assets/no-master-toleration/k8s/) to see if the policy is working as expected.

1. The [first pod](./assets/no-master-toleration/k8s/test-pod-master-toleration.yaml) defines a toleration for the master node taints:

    ~~~yaml
    tolerations:
    - key: "node-role.kubernetes.io/master"
      effect: "NoSchedule"
    ~~~

2. The [second pod](./assets/no-master-toleration/k8s/test-pod-all-tolerations.yaml) defines a toleration for all taints in the node (where master taint may very well be one of them):

    > **NOTE**: In our `Constraint` we can define if we allow (or not) this kind of toleration by setting the `Constraint` parameter `allowGlobalToleration` to either `true` (allow) or `false` (not allow).

    ~~~yaml
    tolerations:
    - operator: "Exists"
    ~~~

3. If we try to create the first pod in our test namespace this is what we get:

    ~~~sh
    oc create -f assets/no-master-toleration/k8s/test-pod-master-toleration.yaml

    Error from server ([master-node-or-global-toleration] Toleration is not allowed for taint {"effect": "NoSchedule", "key": "node-role.kubernetes.io/master", "value": ""}): error when creating "test-pod-master-toleration.yaml": admission webhook "validation.gatekeeper.sh" denied the request: [master-node-or-global-toleration] Toleration is not allowed for taint {"effect": "NoSchedule", "key": "node-role.kubernetes.io/master", "value": ""}
    ~~~

4. If we try to create the second pod this is what we get:

    > **NOTE**: We have the `allowGlobalToleration` parameter set to `false`.

    ~~~sh
    oc create -f assets/no-master-toleration/k8s/test-pod-all-tolerations.yaml

    Error from server ([master-node-or-global-toleration] Global tolerations not allowed for taint {"effect": "NoSchedule", "key": "node-role.kubernetes.io/master", "value": ""}): error when creating "test-pod-all-tolerations.yaml": admission webhook "validation.gatekeeper.sh" denied the request: [master-node-or-global-toleration] Global tolerations not allowed for taint {"effect": "NoSchedule", "key": "node-role.kubernetes.io/master", "value": ""}
    ~~~

5. If we try to create these pods in a namespace where we are not enforcing this policy (like `kube-system`), the pods will be created without issues:

    ~~~sh
    oc -n kube-system create -f assets/no-master-toleration/k8s/test-pod-master-toleration.yaml -f assets/no-master-toleration/k8s/test-pod-all-tolerations.yaml

    pod/test-pod-master-toleration created
    pod/test-pod-all-tolerations created
    ~~~

## **Potential Next Steps**

Explore if the policy can be updated, so users from a given group can define master taints toleration in any namespace.
