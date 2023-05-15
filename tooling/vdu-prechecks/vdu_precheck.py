#!/usr/bin/env python

'''
Script to check whether a server is ready to be used for a vDU, via redfish
'''

import argparse
import pprint
import requests
import urllib3


parser = argparse.ArgumentParser(
    prog='vdu_precheck.py',
    description='queries redfish to determine if a system is ready to run a vDU workload'
)
parser.add_argument("-i","--ip", help="redfish ip", required=True)
parser.add_argument("-u","--user", help="redfish user", required=True)
parser.add_argument("-p","--password", help="redfish password", required=True)
parser.add_argument("-t","--type", help="vdu type (mb vs. lb)", required=True)
parser.add_argument("-d","--debug", help="enable debugging", action="store_true")
parser.add_argument("-v","--verify", help="ssl verify", action="store_true")
args = parser.parse_args()

if not args.verify:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

reference_bios = {
    "HPE": {
        # from partner
        "ProcessorConfigTDPLevel": "Level2",
        "EnhancedProcPerf": "Enabled",
        "Sriov": "Enabled",
        "SubNumaClustering": "Disabled",
        "NumaGroupSizeOpt": "Flat",
        "IntelPriorityBaseFreq": "Enabled",
        "ProcX2Apic": "Enabled",
        "MemPatrolScrubbing": "Disabled",
        "ThermalConfig": "OptimalCooling",
        # rh docs
        "UncoreFreqScaling": "Maximum",
        "ProcTurbo": "Enabled",
    },
    "Dell Inc.": {
        # from partner
        "ProcConfigTdp": "Level2",
        # EnhancedProcPerf
        "SriovGlobalEnable": "Enabled",
        "SubNumaCluster": "Disabled",
        # NumaGroupSizeOpt
        # IntelPriorityBaseFreq
        "ProcX2Apic": "Enabled",
        "MemPatrolScrub": "Standard",
        # ThermalConfig
        # rh docs
        "UncoreFrequency": "Disabled",
        "ProcC1E": "Disabled",
        "ProcTurboMode": "Enabled"
    }
}

supported_nics = ['E810', 'XXV710']

dpp = pprint.PrettyPrinter(indent=2)

def get_url(url):
    '''
    retrives a URL and returns the json formatted response
    '''

    request = requests.get(url, verify=args.verify, auth=(args.user, args.password))
    return request.json()

def get_endpoint():
    '''
    determines what path to use to query redfish for system data
    '''

    url = f"https://{args.ip}/redfish/v1/Systems"
    sys_data = get_url(url)
    sep = sys_data['Members'][0]['@odata.id']
    return sep

def get_vendor(sep):
    '''
    returns the vendor of a system
    different vendors implement redfish in different ways
    '''
    url = f"https://{args.ip}{sep}"
    vendor = get_url(url)['Manufacturer']
    return vendor

def check_bios(sep, vendor):
    '''
    check whether a system's curent BIOS configuration is compliant with
    recommended settings for a vDU
    '''

    url = f"https://{args.ip}{sep}/Bios"
    bios = get_url(url)
    bios = bios['Attributes']

    errors = False
    for key in reference_bios[vendor].keys():
        if key in bios:
            if args.debug:
                print(f"want: {key}: {reference_bios[vendor][key]}")
                print(f"have: {key}: {bios[key]}")
            if reference_bios[vendor][key] != bios[key]:
                print("BIOS mismatch found")
                errors = True
                print(f"want: {key}: {reference_bios[vendor][key]}")
                print(f"have: {key}: {bios[key]}")
        else:
            print(f"key not found: {key}")
            errors = True
    if not errors:
        print("BIOS: ok")


def get_nics(sep, vendor):
    '''
    displays the details of any supported Ethernet devices discovered on the system
    '''

    nics = []

    if vendor == "HPE":
        url = f"https://{args.ip}{sep}/BaseNetworkAdapters"
    elif vendor == "Dell Inc.":
        url = f"https://{args.ip}{sep}/NetworkAdapters"
    else:
        print(f"unsupported server vendor: {vendor}")
        return

    members = get_url(url)['Members']
    nics = []
    for nic in members:
        url = f"https://{args.ip}{nic['@odata.id']}"
        nic_data = get_url(url)
        nic = parse_nic(nic_data, vendor)
        if nic:
            if isinstance(nic, list):
                for port in nic:
                    nics.append(port)
            else:
                nics.append(nic)
    if len(nics) == 0:
        print("no supported nics found")
    else:
        print("NICs:")
        dpp.pprint(nics)

def parse_nic(nic_data, vendor):
    '''
    parse nic data based on vendor
    '''

    nics = []

    if vendor == "HPE":
        nic_model = nic_data['Name']
        if supported_nic(nic_model):
            nic_slot = nic_data['Location']
            macs = []
            for port in nic_data['PhysicalPorts']:
                macs.append(port['MacAddress'])
            return {
              'model': nic_model,
              'slot': nic_slot,
              'macs': macs
            }

    if vendor == "Dell Inc.":
        nic_model = nic_data['Model']
        if supported_nic(nic_model):
            #print(nic_data)
            ports = nic_data['NetworkPorts']['@odata.id']
            url = f"https://{args.ip}{ports}"
            members = get_url(url)['Members']
            for member in members:
                url = f"https://{args.ip}{member['@odata.id']}"
                port_data = get_url(url)
                nic_slot = port_data['Id']
                macs = []
                for mac in port_data['AssociatedNetworkAddresses']:
                    macs.append(mac)
                nics.append({
                    'model': nic_model,
                    'slot': nic_slot,
                    'macs': macs
                })
            return nics

    return None

def supported_nic(model):
    '''
    test if a given NIC is supported
    '''

    for supported in supported_nics:
        if supported in model:
            return True

    return False

def get_fec(sep, vendor):
    '''
    confirms whether a FEC (accelerator card) is found in the system
    and if so, the slot it is in
    '''

    if vendor == "HPE":
        url = f"https://{args.ip}{sep}/PCIDevices"
        members = get_url(url)['Members']
        for device in members:
            url = f"https://{args.ip}{device['@odata.id']}"
            device_data = get_url(url)
            device = device_data['Name']
            if 'Silicom Lisbon2' in device:
                print(f"FEC: discovered in {device_data['DeviceLocation']}")

def get_disks(sep, vendor):
    '''
    lists all disks in a system along with their serial number, location and type
    '''

    disks = []

    if vendor == "HPE":
        url = f"https://{args.ip}{sep}/Storage"
        members = get_url(url)['Members']
    elif vendor == "Dell Inc.":
        url = f"https://{args.ip}{sep}/Storage/CPU.1"
        members = get_url(url)
    else:
        print(f"unsupported server vendor: {vendor}")
        return

    if vendor == "HPE":
        for member in members:
            url = f"https://{args.ip}{member['@odata.id']}"
            drives = get_url(url)['Drives']
            for drive in drives:
                url = f"https://{args.ip}{drive['@odata.id']}"
                drive_data = get_url(url)
                model = drive_data['Model']
                media_type = drive_data['MediaType']
                serial = drive_data['SerialNumber']
                slot = drive_data['PhysicalLocation']['PartLocation']['ServiceLabel']
                disks.append({
                    'model': model,
                    'type': media_type,
                    'serial': serial,
                    'slot': slot
                })

    if vendor == "Dell Inc.":
        drives = members['Drives']
        for drive in drives:
            url = f"https://{args.ip}{drive['@odata.id']}"
            drive_data = get_url(url)
            model = drive_data['Model']
            media_type = drive_data['MediaType']
            serial = drive_data['SerialNumber']
            slot = drive_data['Name']
            disks.append({
                'model': model,
                'type': media_type,
                'serial': serial,
                'slot': slot
            })

    if len(disks) == 0:
        print("no disks found")
    else:
        print("Disks:")
        dpp.pprint(disks)

def main():
    '''
    report on various aspects of a system to determine if its ready
    to run a vDU workload
    '''

    sep = get_endpoint()
    vendor = get_vendor(sep)
    print(f"checking BIOS for {vendor} system @ {args.ip}")

    if vendor in reference_bios:
        check_bios(sep, vendor)
    else:
        print(f"no reference BIOS config for {vendor}")

    get_nics(sep, vendor)
    get_disks(sep, vendor)

    if args.type == 'mb':
        get_fec(sep, vendor)

main()
