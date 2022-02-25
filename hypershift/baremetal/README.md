# HyperShift on OpenShift on Baremetal

:warning: The work exposed here is not supported in any way by Red Hat, this is the result of exploratory work. Use at your own risk.

## **agent vs none**

To simplify things, using the `none` provider means adding the worker requires to boot it using a generic RHCOS iso and perform some manual steps such as
specify the ignition URL. It also requires to approve the `csr` when the workers are added to the cluster. The whole process can be automated but it
depends on the environment.
However, using `agent` leverages all the plumbing already included in the Assisted Service and the Baremetal Operator, meaning the process of adding
workers is performed automatically (the host is managed by the Baremetal Host and installed with a custom image built by the Assisted Service).

* [HyperShift + Bare Metal workers using 'none' provider](./none.md)
* [HyperShift + Bare Metal workers using 'agent' provider](./agent.md)