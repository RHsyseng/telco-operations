# vdu_precheck.py

vDU systems at the edge need specific [firmware values](https://docs.openshift.com/container-platform/4.12/scalability_and_performance/ztp_far_edge/ztp-reference-cluster-configuration-for-vdu.html) set to meet the stringent performance requirements for telco workloads. This script will query a system via redfish to compare that node's current firmware configuration vs. the recommended settings for that particular vendor. It will also report on the system's Ethernet interfaces and hard drives, which can be used in a [SiteConfig](https://docs.openshift.com/container-platform/4.12/scalability_and_performance/ztp_far_edge/ztp-deploying-far-edge-sites.html#ztp-deploying-a-site_ztp-deploying-far-edge-sites) when deploying a new edge site.

## Usage
~~~
$ ./vdu_precheck.py -h
usage: vdu_precheck.py [-h] -i IP -u USER -p PASSWORD -t TYPE [-d] [-v]

queries redfish to determine if a system is ready to run a vDU workload

options:
  -h, --help            show this help message and exit
  -i IP, --ip IP        redfish ip
  -u USER, --user USER  redfish user
  -p PASSWORD, --password PASSWORD
                        redfish password
  -t TYPE, --type TYPE  vdu type (mb vs. lb)
  -d, --debug           enable debugging
  -v, --verify          ssl verify
  ~~~


### Example

~~~
$ ./vdu_precheck.py  -i 192.168.42.24 -u root -p P@ssw0rd -t mb 
checking BIOS for HPE system @ 192.168.42.24
BIOS mismatch found
want: EnhancedProcPerf: Enabled
have: EnhancedProcPerf: Disabled
BIOS mismatch found
want: MemPatrolScrubbing: Disabled
have: MemPatrolScrubbing: Enabled
NICs:
[ { 'macs': [ 'de:ea:be:ee:ff:e0',
              'de:ea:be:ee:ff:e1',
              'de:ea:be:ee:ff:e2',
              'de:ea:be:ee:ff:e3'],
    'model': 'Intel(R) Eth E810-XXVDA4',
    'slot': 'PCI-E Slot 1'},
  { 'macs': [ 'de:ea:be:5e:1f:4a',
              'de:ea:be:5e:1f:4b',
              'de:ea:be:5e:1f:4c',
              'de:ea:be:5e:1f:4d'],
    'model': 'Intel(R) Eth E810-XXVDA4',
    'slot': 'PCI-E Slot 2'}]
Disks:
[ { 'model': 'SAMSUNG MZ1LB960HAJQ-00007',
    'serial': 'SERIALNUM1234',
    'slot': 'Slot 12',
    'type': 'SSD'},
  { 'model': 'SAMSUNG MZ1LB960HAJQ-00007',
    'serial': 'SERIALNUM5678',
    'slot': 'Slot 13',
    'type': 'SSD'}]
FEC: discovered in PCI-E Slot 3
~~~

### TODO

* More systems to be added overtime.