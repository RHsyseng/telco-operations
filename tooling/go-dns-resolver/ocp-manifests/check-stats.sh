#!/bin/bash

APP_ROUTE=$(oc -n dns-app-tests get route dns-app -o jsonpath=https://{.spec.host}/metrics)

while true
do
  date +"%Y/%m/%d %H:%M:%S"
  curl -sk ${APP_ROUTE} | grep -v ^#
  sleep 5
done
