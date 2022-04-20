#!/bin/bash

#### This script has to unmount the iso from the server's virtualmedia and return 0 if operation succeeded, 1 otherwise

# Disconnect image
/opt/dell/srvadmin/bin/idracadm7 -r 192.168.1.10 -u root -p calvin remoteimage -d
if [ $? -eq 0 ]; then
  exit 0
else
  exit 1
fi
