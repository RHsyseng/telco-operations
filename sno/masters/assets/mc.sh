#!/usr/bin/env bash 

export FORCEDNS=$(cat 99-forcedns | base64 -w0)
export COREDNS=$(cat coredns.yml | base64 -w0)
export COREFILE=$(cat Corefile.template | base64 -w0)
export KEEPALIVED=$(cat keepalived.yml | base64 -w0)
export KEEPALIVEDCONF=$(cat keepalived.conf.template | base64 -w0)

envsubst < mc.yml.sample > mc.yml
