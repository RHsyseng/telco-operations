import netifaces
from ipaddress import ip_address, ip_network
import os
import sys


def get_ip(machine_cidr):
    network = ip_network(machine_cidr)
    for interface in netifaces.interfaces():
        addresses = netifaces.ifaddresses(interface)
        for address_family in (netifaces.AF_INET, netifaces.AF_INET6):
            family_addresses = addresses.get(address_family)
            if not family_addresses:
                continue
            for address in family_addresses:
                ip = address['addr']
                if ip.startswith('fe'):
                    continue
                elif ip_address(ip) in network:
                    return ip


if 'CIDR' not in os.environ:
    print("Missing CIDR env variable")
    sys.exit(1)
machine_cidr = os.environ.get('CIDR')
print(get_ip(machine_cidr))
