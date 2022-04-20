#!/bin/bash

#### This script has to set the server's boot to once from cd and return 0 if operation succeeded, 1 otherwise

/opt/dell/srvadmin/bin/idracadm7 -r 192.168.1.10 -u root -p calvin set iDRAC.VirtualMedia.BootOnce 1
if [ $? -eq 0 ]; then
  /opt/dell/srvadmin/bin/idracadm7 -r 192.168.1.10 -u root -p calvin set iDRAC.ServerBoot.FirstBootDevice VCD-DVD
  if [ $? -eq 0 ]; then
    exit 0
  else
    exit 1
  fi
else
  exit 1
fi
