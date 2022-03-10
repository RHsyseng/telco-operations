# **Run PolicyGenTool Kustomize Plugins Locally**

This document covers how to run the [PolicyGenTool Generator plugins](https://github.com/openshift-kni/cnf-features-deploy/tree/master/ztp) locally.

1. Get Kustomize and install it, you can get it from the [releases page](https://github.com/kubernetes-sigs/kustomize/releases/).
2. Extract plugins from the PolicyGenTool image to your user's plugin directory:

    ~~~sh
    mkdir -p ~/.config/kustomize/plugin
    podman cp $(podman create --name policgentool --rm quay.io/redhat_emp1/ztp-site-generator:4.10.0-1):/kustomize/plugin/ran.openshift.io ~/.config/kustomize/plugin/
    podman rm -f policgentool
    ~~~

3. Run Kustomize with plugins enabled:

    > :exclamation: `site-configs` is a folder that has `SiteConfig` resources. The same applies to `PolicyGenTemplates` resources.

    ~~~sh
    kustomize build site-configs/ --enable-alpha-plugins
    ~~~
