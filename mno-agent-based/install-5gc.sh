#! /usr/bin/env bash
set -euoxE pipefail

# ssh into workstation
ip add s
read -p -r
# review network req for workstation, bmc and machine network

openshift-install version
read -p -r
# https://mirror.openshift.com/pub/openshift-v4/clients/ocp/4.12.13/

mkdir -p deployments/ && cp -r 5gc-template deployments/5gc
read -p -r
# tree before,after

cat secret.yaml >>  ./deployments/5gc/install-config.yaml
read -p -r
# sshpubkey and readonly pull secret

openshift-install agent create image --log-level info  --dir ./deployments/5gc
read -p -r
# discovery ISO created // nmstatectl required

mv ./deployments/5gc/agent.x86_64.iso  /isos/agent-5gc.iso
read -p -r
# python3 -m http.server 9000 -d /isos

### "Mount and booting the ISO in the servers using RedFish"

# shellcheck disable=1090
source ./redfish-actions/sushy.sh  # BMC_TYPE=hpe|dell|sushy

for node in \
  https://192.168.100.100:8000/redfish/v1/Systems/11111111-1111-1111-1111-111111111110 \
  https://192.168.100.100:8000/redfish/v1/Systems/11111111-1111-1111-1111-111111111111 \
  https://192.168.100.100:8000/redfish/v1/Systems/11111111-1111-1111-1111-111111111112 ;
do
  power_off "$node"
  media_eject "$node"
  media_insert "$node" http://192.168.100.200:9000/agent-5gc.iso
  boot_once "$node"
  power_on "$node"
done

read -p -r
# kcli console  5gc-m0; kcli console 5gc-m1; kcli console 5gc-m2

cat << EOF
export KUBECONFIG=./deployments/5gc/auth/kubeconfig
openshift-install agent wait-for install-complete --log-level info --dir "./deployments/5gc"
EOF

# talk about install-config, agent-config
# talk about day0 operation
# talk about dual stack VIPs // br-ex
