#!/usr/bin/env bash

CIDR=$1
IP=$(podman run --rm --net host -e CIDR=$CIDR quay.io/karmab/nodeip-hack)
cat << EOF > /etc/systemd/system/kubelet.service.d/20-nodenet.conf
[Service]
Environment="KUBELET_NODE_IP=$IP" "KUBELET_NODE_IPS=$IP"
EOF
cat << EOF > /etc/systemd/system/crio.service.d/20-nodenet.conf
[Service]
Environment="CONTAINER_STREAM_ADDRESS=$IP"
EOF
