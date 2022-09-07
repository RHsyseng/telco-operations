# **Deploying an OpenShift Cluster with software raid using Assisted Installer**

This document briefly describes how to run a deployment of an OpenShift Cluster through Assisted Installer where software raid needs to be set up.

We will use [Assisted Installer CLI](https://github.com/karmab/aicli) in order to interact with the Assisted Service API in a CLI fashion.

The approach involves using the API to inject an extra ignition config on the hosts that will trigger the configuration of the raid.

## **Preparing the ignition file content**

We prepare a file to indicate which software raid is to be configured, and which disks are part of it.

~~~json
{
  "ignition": {
    "version": "3.2.0"
  },
  "storage": {
    "disks": [
      {
        "device": "/dev/vda",
        "partitions": [
          {
            "label": "bios-1",
            "sizeMiB": 1,
            "typeGuid": "21686148-6449-6E6F-744E-656564454649"
          },
          {
            "label": "esp-1",
            "sizeMiB": 127,
            "typeGuid": "C12A7328-F81F-11D2-BA4B-00A0C93EC93B"
          },
          {
            "label": "boot-1",
            "sizeMiB": 384
          },
          {
            "label": "root-1"
          }
        ],
        "wipeTable": true
      },
      {
        "device": "/dev/vdb",
        "partitions": [
          {
            "label": "bios-2",
            "sizeMiB": 1,
            "typeGuid": "21686148-6449-6E6F-744E-656564454649"
          },
          {
            "label": "esp-2",
            "sizeMiB": 127,
            "typeGuid": "C12A7328-F81F-11D2-BA4B-00A0C93EC93B"
          },
          {
            "label": "boot-2",
            "sizeMiB": 384
          },
          {
            "label": "root-2"
          }
        ],
        "wipeTable": true
      }
    ],
    "filesystems": [
      {
        "device": "/dev/disk/by-partlabel/esp-1",
        "format": "vfat",
        "label": "esp-1",
        "wipeFilesystem": true
      },
      {
        "device": "/dev/disk/by-partlabel/esp-2",
        "format": "vfat",
        "label": "esp-2",
        "wipeFilesystem": true
      },
      {
        "device": "/dev/md/md-boot",
        "format": "ext4",
        "label": "boot",
        "wipeFilesystem": true
      },
      {
        "device": "/dev/md/md-root",
        "format": "xfs",
        "label": "root",
        "wipeFilesystem": true
      }
    ],
    "raid": [
      {
        "devices": [
          "/dev/disk/by-partlabel/boot-1",
          "/dev/disk/by-partlabel/boot-2"
        ],
        "level": "raid1",
        "name": "md-boot",
        "options": [
          "--metadata=1.0"
        ]
      },
      {
        "devices": [
          "/dev/disk/by-partlabel/root-1",
          "/dev/disk/by-partlabel/root-2"
        ],
        "level": "raid1",
        "name": "md-root"
      }
    ]
  }
}
~~~

In the remainder of this document, we will refer to the file [raid.ign](raid.ign) which contains this same configuration.

Note that you will have to adjust the disk names to match your own environment.

## **Applying the custom ignition**

Once the nodes are discovered, we can use the following command on a per host basis to have the ignition applied at first boot:

~~~
aicli update host myhost -P ignition_file=raid.ign
~~~

At this point, when the node first boots, raid will be configured, as visible in the logs:

~~~
Sep 06 22:37:03 localhost systemd[1]: Starting Ignition (disks)...
Sep 06 22:37:03 localhost ignition[1322]: Ignition 2.14.0
Sep 06 22:37:03 localhost ignition[1322]: Stage: disks
Sep 06 22:37:03 localhost ignition[1322]: reading system config file "/usr/lib/ignition/base.d/00-core.ign"
Sep 06 22:37:03 localhost ignition[1322]: parsing config with SHA512: ff6a5153be363997e4d5d3ea8cc4048373a457c48c4a5b134a08a30aacd167c1e0f099f0bdf1e24c99ad180628cd02b767b863b5fe3a8fce3fe1886847eb8e2e
Sep 06 22:37:03 localhost ignition[1322]: no config dir at "/usr/lib/ignition/base.platform.d/metal"
Sep 06 22:37:03 localhost ignition[1322]: disks: createPartitions: op(1): [started]  waiting for devices [/dev/vda /dev/vdb]
Sep 06 22:37:03 localhost ignition[1322]: disks: createPartitions: op(1): [finished] waiting for devices [/dev/vda /dev/vdb]
Sep 06 22:37:03 localhost ignition[1322]: disks: createPartitions: created device alias for "/dev/vda": "/run/ignition/dev_aliases/dev/vda" -> "/dev/vda"
Sep 06 22:37:03 localhost ignition[1322]: disks: createPartitions: created device alias for "/dev/vdb": "/run/ignition/dev_aliases/dev/vdb" -> "/dev/vdb"
Sep 06 22:37:03 localhost systemd-journald[475]: Missed 10 kernel messages
Sep 06 22:37:03 localhost kernel:  vda: vda1 vda2 vda3 vda4
Sep 06 22:37:03 localhost ignition[1322]: disks: createPartitions: op(2): [started]  partitioning "/run/ignition/dev_aliases/dev/vda"
Sep 06 22:37:03 localhost ignition[1322]: disks: createPartitions: op(2): wiping partition table requested on "/run/ignition/dev_aliases/dev/vda"
Sep 06 22:37:03 localhost ignition[1322]: disks: createPartitions: op(2): running sgdisk with options: [--zap-all /run/ignition/dev_aliases/dev/vda]
Sep 06 22:37:03 localhost ignition[1322]: disks: createPartitions: op(2): op(3): [started]  deleting 0 partitions and creating 0 partitions on "/run/ignition/dev_aliases/dev/vda"
Sep 06 22:37:03 localhost ignition[1322]: disks: createPartitions: op(2): op(3): executing: "sgdisk" "--zap-all" "/run/ignition/dev_aliases/dev/vda"
Sep 06 22:37:08 localhost ignition[1322]: disks: createPartitions: op(2): op(3): [finished] deleting 0 partitions and creating 0 partitions on "/run/ignition/dev_aliases/dev/vda"
Sep 06 22:37:08 localhost ignition[1322]: disks: createPartitions: op(2): op(4): [started]  reading partition table of "/run/ignition/dev_aliases/dev/vda"
Sep 06 22:37:08 localhost ignition[1322]: disks: createPartitions: op(2): op(4): [finished] reading partition table of "/run/ignition/dev_aliases/dev/vda"
Sep 06 22:37:08 localhost ignition[1322]: disks: createPartitions: op(2): running sgdisk with options: [--pretend --new=0:0:+2048 --typecode=0:21686148-6449-6E6F-744E-656564454649 --new=0:0:+260096 --typecode=0:C12A7328-F81F-11D2-BA4B-00A0C93EC93B --new=0:0:+786432 --new=0:0:+0 /run/ignition/dev_aliases/dev/vda]
Sep 06 22:37:08 localhost ignition[1322]: disks: createPartitions: op(2): running sgdisk with options: [--new=0:0:+2048 --change-name=0:bios-1 --typecode=0:21686148-6449-6E6F-744E-656564454649 --new=0:0:+260096 --change-name=0:esp-1 --typecode=0:C12A7328-F81F-11D2-BA4B-00A0C93EC93B --new=0:0:+786432 --change-name=0:boot-1 --new=0:0:+0 --change-name=0:root-1 /run/ignition/dev_aliases/dev/vda]
Sep 06 22:37:08 localhost ignition[1322]: disks: createPartitions: op(2): op(5): [started]  deleting 0 partitions and creating 4 partitions on "/run/ignition/dev_aliases/dev/vda"
Sep 06 22:37:08 localhost ignition[1322]: disks: createPartitions: op(2): op(5): executing: "sgdisk" "--new=0:0:+2048" "--change-name=0:bios-1" "--typecode=0:21686148-6449-6E6F-744E-656564454649" "--new=0:0:+260096" "--change-name=0:esp-1" "--typecode=0:C12A7328-F81F-11D2-BA4B-00A0C93EC93B" "--new=0:0:+786432" "--change-name=0:boot-1" "--new=0:0:+0" "--change-name=0:root-1" "/run/ignition/dev_aliases/dev/vda"
Sep 06 22:37:09 localhost ignition[1322]: disks: createPartitions: op(2): op(5): [finished] deleting 0 partitions and creating 4 partitions on "/run/ignition/dev_aliases/dev/vda"
Sep 06 22:37:09 localhost systemd-journald[475]: Missed 10 kernel messages
Sep 06 22:37:09 localhost kernel:  vda: vda1 vda2 vda3 vda4
Sep 06 22:37:09 localhost ignition[1322]: disks: createPartitions: op(2): [finished] partitioning "/run/ignition/dev_aliases/dev/vda"
Sep 06 22:37:09 localhost ignition[1322]: disks: createPartitions: op(6): [started]  partitioning "/run/ignition/dev_aliases/dev/vdb"
Sep 06 22:37:09 localhost ignition[1322]: disks: createPartitions: op(6): wiping partition table requested on "/run/ignition/dev_aliases/dev/vdb"
Sep 06 22:37:09 localhost ignition[1322]: disks: createPartitions: op(6): running sgdisk with options: [--zap-all /run/ignition/dev_aliases/dev/vdb]
Sep 06 22:37:09 localhost ignition[1322]: disks: createPartitions: op(6): op(7): [started]  deleting 0 partitions and creating 0 partitions on "/run/ignition/dev_aliases/dev/vdb"
Sep 06 22:37:09 localhost ignition[1322]: disks: createPartitions: op(6): op(7): executing: "sgdisk" "--zap-all" "/run/ignition/dev_aliases/dev/vdb"
Sep 06 22:37:10 localhost ignition[1322]: disks: createPartitions: op(6): op(7): [finished] deleting 0 partitions and creating 0 partitions on "/run/ignition/dev_aliases/dev/vdb"
Sep 06 22:37:10 localhost ignition[1322]: disks: createPartitions: op(6): op(8): [started]  reading partition table of "/run/ignition/dev_aliases/dev/vdb"
Sep 06 22:37:10 localhost ignition[1322]: disks: createPartitions: op(6): op(8): [finished] reading partition table of "/run/ignition/dev_aliases/dev/vdb"
Sep 06 22:37:10 localhost ignition[1322]: disks: createPartitions: op(6): running sgdisk with options: [--pretend --new=0:0:+2048 --typecode=0:21686148-6449-6E6F-744E-656564454649 --new=0:0:+260096 --typecode=0:C12A7328-F81F-11D2-BA4B-00A0C93EC93B --new=0:0:+786432 --new=0:0:+0 /run/ignition/dev_aliases/dev/vdb]
Sep 06 22:37:10 localhost ignition[1322]: disks: createPartitions: op(6): running sgdisk with options: [--new=0:0:+2048 --change-name=0:bios-2 --typecode=0:21686148-6449-6E6F-744E-656564454649 --new=0:0:+260096 --change-name=0:esp-2 --typecode=0:C12A7328-F81F-11D2-BA4B-00A0C93EC93B --new=0:0:+786432 --change-name=0:boot-2 --new=0:0:+0 --change-name=0:root-2 /run/ignition/dev_aliases/dev/vdb]
Sep 06 22:37:10 localhost ignition[1322]: disks: createPartitions: op(6): op(9): [started]  deleting 0 partitions and creating 4 partitions on "/run/ignition/dev_aliases/dev/vdb"
Sep 06 22:37:10 localhost ignition[1322]: disks: createPartitions: op(6): op(9): executing: "sgdisk" "--new=0:0:+2048" "--change-name=0:bios-2" "--typecode=0:21686148-6449-6E6F-744E-656564454649" "--new=0:0:+260096" "--change-name=0:esp-2" "--typecode=0:C12A7328-F81F-11D2-BA4B-00A0C93EC93B" "--new=0:0:+786432" "--change-name=0:boot-2" "--new=0:0:+0" "--change-name=0:root-2" "/run/ignition/dev_aliases/dev/vdb"
Sep 06 22:37:11 localhost systemd-journald[475]: Missed 12 kernel messages
Sep 06 22:37:11 localhost kernel:  vdb: vdb1 vdb2 vdb3 vdb4
Sep 06 22:37:11 localhost ignition[1322]: disks: createPartitions: op(6): op(9): [finished] deleting 0 partitions and creating 4 partitions on "/run/ignition/dev_aliases/dev/vdb"
Sep 06 22:37:11 localhost ignition[1322]: disks: createPartitions: op(6): [finished] partitioning "/run/ignition/dev_aliases/dev/vdb"
Sep 06 22:37:11 localhost ignition[1322]: disks: createRaids: op(a): [started]  waiting for devices [/dev/disk/by-partlabel/boot-1 /dev/disk/by-partlabel/boot-2 /dev/disk/by-partlabel/root-1 /dev/disk/by-partlabel/root-2]
Sep 06 22:37:11 localhost systemd[1]: Found device /dev/disk/by-partlabel/boot-2.
Sep 06 22:37:11 localhost systemd[1]: Found device /dev/disk/by-partlabel/root-2.
Sep 06 22:37:11 localhost ignition[1322]: disks: createRaids: op(a): [finished] waiting for devices [/dev/disk/by-partlabel/boot-1 /dev/disk/by-partlabel/boot-2 /dev/disk/by-partlabel/root-1 /dev/disk/by-partlabel/root-2]
Sep 06 22:37:11 localhost ignition[1322]: disks: createRaids: created device alias for "/dev/disk/by-partlabel/boot-1": "/run/ignition/dev_aliases/dev/disk/by-partlabel/boot-1" -> "/dev/vda3"
Sep 06 22:37:11 localhost ignition[1322]: disks: createRaids: created device alias for "/dev/disk/by-partlabel/boot-2": "/run/ignition/dev_aliases/dev/disk/by-partlabel/boot-2" -> "/dev/vdb3"
Sep 06 22:37:11 localhost ignition[1322]: disks: createRaids: created device alias for "/dev/disk/by-partlabel/root-1": "/run/ignition/dev_aliases/dev/disk/by-partlabel/root-1" -> "/dev/vda4"
Sep 06 22:37:11 localhost ignition[1322]: disks: createRaids: created device alias for "/dev/disk/by-partlabel/root-2": "/run/ignition/dev_aliases/dev/disk/by-partlabel/root-2" -> "/dev/vdb4"
Sep 06 22:37:11 localhost ignition[1322]: disks: createRaids: op(b): [started]  creating "md-boot"
Sep 06 22:37:11 localhost ignition[1322]: disks: createRaids: op(b): executing: "mdadm" "--create" "md-boot" "--force" "--run" "--homehost" "any" "--level" "raid1" "--raid-devices" "2" "--metadata=1.0" "/run/ignition/dev_aliases/dev/disk/by-partlabel/boot-1" "/run/ignition/dev_aliases/dev/disk/by-partlabel/boot-2"
Sep 06 22:37:11 localhost systemd-journald[475]: Missed 11 kernel messages
Sep 06 22:37:11 localhost kernel: md/raid1:md127: not clean -- starting background reconstruction
Sep 06 22:37:11 localhost kernel: md/raid1:md127: active with 2 out of 2 mirrors
Sep 06 22:37:11 localhost kernel: md127: detected capacity change from 0 to 402587648
Sep 06 22:37:11 localhost kernel: md: resync of RAID array md127
Sep 06 22:37:11 localhost ignition[1322]: disks: createRaids: op(b): [finished] creating "md-boot"
Sep 06 22:37:11 localhost ignition[1322]: disks: createRaids: op(c): [started]  creating "md-root"
Sep 06 22:37:11 localhost ignition[1322]: disks: createRaids: op(c): executing: "mdadm" "--create" "md-root" "--force" "--run" "--homehost" "any" "--level" "raid1" "--raid-devices" "2" "/run/ignition/dev_aliases/dev/disk/by-partlabel/root-1" "/run/ignition/dev_aliases/dev/disk/by-partlabel/root-2"
Sep 06 22:37:11 localhost systemd-journald[475]: Missed 2 kernel messages
Sep 06 22:37:11 localhost kernel: md/raid1:md126: not clean -- starting background reconstruction
Sep 06 22:37:11 localhost kernel: md/raid1:md126: active with 2 out of 2 mirrors
Sep 06 22:37:11 localhost kernel: md126: detected capacity change from 0 to 214075113472
Sep 06 22:37:11 localhost kernel: md: delaying resync of md126 until md127 has finished (they share one or more physical units)
Sep 06 22:37:11 localhost ignition[1322]: disks: createRaids: op(c): [finished] creating "md-root"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(d): [started]  waiting for devices [/dev/disk/by-partlabel/esp-1 /dev/disk/by-partlabel/esp-2 /dev/md/md-boot /dev/md/md-root]
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(d): [finished] waiting for devices [/dev/disk/by-partlabel/esp-1 /dev/disk/by-partlabel/esp-2 /dev/md/md-boot /dev/md/md-root]
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: created device alias for "/dev/disk/by-partlabel/esp-1": "/run/ignition/dev_aliases/dev/disk/by-partlabel/esp-1" -> "/dev/vda2"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: created device alias for "/dev/disk/by-partlabel/esp-2": "/run/ignition/dev_aliases/dev/disk/by-partlabel/esp-2" -> "/dev/vdb2"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: created device alias for "/dev/md/md-boot": "/run/ignition/dev_aliases/dev/md/md-boot" -> "/dev/md127"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: created device alias for "/dev/md/md-root": "/run/ignition/dev_aliases/dev/md/md-root" -> "/dev/md126"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): [started]  determining filesystem type of "/dev/md/md-boot"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(11): [started]  determining filesystem type of "/dev/md/md-root"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): [started]  determining filesystem type of "/dev/disk/by-partlabel/esp-1"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): [started]  determining filesystem type of "/dev/disk/by-partlabel/esp-2"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(11): [finished] determining filesystem type of "/dev/disk/by-partlabel/esp-2"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): found  filesystem at "/dev/disk/by-partlabel/esp-2" with uuid "" and label ""
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(12): [started]  wiping filesystem signatures from "/run/ignition/dev_aliases/dev/disk/by-partlabel/esp-2"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(12): executing: "wipefs" "-a" "/run/ignition/dev_aliases/dev/disk/by-partlabel/esp-2"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(12): [finished] determining filesystem type of "/dev/md/md-root"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): found  filesystem at "/dev/md/md-root" with uuid "" and label ""
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(13): [started]  wiping filesystem signatures from "/run/ignition/dev_aliases/dev/md/md-root"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(13): executing: "wipefs" "-a" "/run/ignition/dev_aliases/dev/md/md-root"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(13): [finished] determining filesystem type of "/dev/disk/by-partlabel/esp-1"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): found vfat filesystem at "/dev/disk/by-partlabel/esp-1" with uuid "C2E6-C3A6" and label "EFI-SYSTEM"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(14): [started]  wiping filesystem signatures from "/run/ignition/dev_aliases/dev/disk/by-partlabel/esp-1"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(14): executing: "wipefs" "-a" "/run/ignition/dev_aliases/dev/disk/by-partlabel/esp-1"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(14): [finished] wiping filesystem signatures from "/run/ignition/dev_aliases/dev/md/md-root"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(15): [started]  creating "xfs" filesystem on "/run/ignition/dev_aliases/dev/md/md-root"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(15): executing: "mkfs.xfs" "-f" "-L" "root" "/run/ignition/dev_aliases/dev/md/md-root"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(15): [finished] wiping filesystem signatures from "/run/ignition/dev_aliases/dev/disk/by-partlabel/esp-1"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(16): [started]  creating "vfat" filesystem on "/run/ignition/dev_aliases/dev/disk/by-partlabel/esp-1"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(16): executing: "mkfs.fat" "-n" "esp-1" "/run/ignition/dev_aliases/dev/disk/by-partlabel/esp-1"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(16): [finished] wiping filesystem signatures from "/run/ignition/dev_aliases/dev/disk/by-partlabel/esp-2"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(17): [started]  creating "vfat" filesystem on "/run/ignition/dev_aliases/dev/disk/by-partlabel/esp-2"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(17): executing: "mkfs.fat" "-n" "esp-2" "/run/ignition/dev_aliases/dev/disk/by-partlabel/esp-2"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): op(17): [finished] creating "vfat" filesystem on "/run/ignition/dev_aliases/dev/disk/by-partlabel/esp-1"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(10): [finished] determining filesystem type of "/dev/md/md-boot"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): found ext4 filesystem at "/dev/md/md-boot" with uuid "9fdcff79-062a-4102-abdb-76a8cb6fb19a" and label "boot"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(18): [started]  wiping filesystem signatures from "/run/ignition/dev_aliases/dev/md/md-boot"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(18): executing: "wipefs" "-a" "/run/ignition/dev_aliases/dev/md/md-boot"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): op(18): [finished] creating "vfat" filesystem on "/run/ignition/dev_aliases/dev/disk/by-partlabel/esp-2"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(f): [finished] wiping filesystem signatures from "/run/ignition/dev_aliases/dev/md/md-boot"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(19): [started]  creating "ext4" filesystem on "/run/ignition/dev_aliases/dev/md/md-boot"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(19): executing: "mkfs.ext4" "-F" "-L" "boot" "/run/ignition/dev_aliases/dev/md/md-boot"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): op(19): [finished] creating "ext4" filesystem on "/run/ignition/dev_aliases/dev/md/md-boot"
Sep 06 22:37:11 localhost ignition[1322]: disks: createFilesystems: op(e): [finished] creating "xfs" filesystem on "/run/ignition/dev_aliases/dev/md/md-root"
Sep 06 22:37:11 localhost ignition[1322]: disks: op(1a): [started]  waiting for udev to settle
Sep 06 22:37:11 localhost ignition[1322]: disks: op(1a): executing: "udevadm" "settle"
Sep 06 22:37:11 localhost ignition[1322]: disks: op(1a): [finished] waiting for udev to settle
Sep 06 22:37:11 localhost ignition[1322]: disks: disks passed
Sep 06 22:37:11 localhost systemd[1]: Started Ignition (disks).
Sep 06 22:37:11 localhost ignition[1322]: Ignition finished successfully
~~~
