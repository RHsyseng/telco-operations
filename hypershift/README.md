# HyperShift on OpenShift

:warning: The work exposed here is not supported in any way by Red Hat, this is the result of exploratory work. Use at your own risk.

HyperShift is middleware for hosting OpenShift control planes at scale that solves for cost and time to provision,
as well as portability cross cloud with strong separation of concerns between management and workloads.
Clusters are fully compliant OpenShift Container Platform (OCP) clusters and are compatible with standard OCP and Kubernetes toolchains.

![High level overview](https://hypershift-docs.netlify.app/images/high-level-overview.png)

More detailed information can be found in the [official website](https://hypershift-docs.netlify.app/)
as well as in the [HyperShift GitHub repository](https://github.com/openshift/hypershift/)

This folder contains different documents to get Hypershift up and running on different platforms.

* [HyperShift + Kubevirt](./kubevirt/README.md)
* [HyperShift + Bare Metal workers using 'none' provider](./baremetal/none.md)
