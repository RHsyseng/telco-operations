#!/usr/bin/env python3

from redfish import Redfish
import sys
import yaml

inventory = sys.argv[1] if len(sys.argv) > 1 else 'inventory'
with open(inventory) as f:
    data = yaml.safe_load(f)['all']['vars']


default_bmc_user = data.get('bmc_user', 'root')
default_bmc_password = data.get('bmc_password', 'calvin')
default_bmc_model = data.get('bmc_model', 'dell')
iso_url = data['iso_url']
hosts = data['hosts']
for host in hosts:
    bmc_url = host.get('bmc_url')
    bmc_user = host.get('bmc_user', default_bmc_user)
    bmc_password = host.get('bmc_password', default_bmc_password)
    bmc_model = host.get('bmc_model', default_bmc_model)
    if bmc_url is not None:
        red = Redfish(bmc_url, bmc_user, bmc_password, model=bmc_model)
        red.set_iso(iso_url)
