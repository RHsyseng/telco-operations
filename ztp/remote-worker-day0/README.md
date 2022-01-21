# ZTP Remote Worker Nodes at day 0

:warning: The work exposed here is not supported in any way by Red Hat, this is the result of exploratory work. Use at your own risk.

We wanted to know if it was possible to deploy a multi-node OpenShift cluster with remote worker nodes at day 0. This operation is already supported as a day 2 action, we will expose the different issues we found and how we were able to overcome these issues.

This work has been tested following two approaches:

1. Using RHACM ZTP capabilities (Assisted Installed)
2. Using ZTP PolicyGenTool (Abstraction of the above)

The work is organized in two folders, you want to read first the work under `ztp-ai` folder and after that you can continue reading `ztp-policygentool`.