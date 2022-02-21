# (ab)Using Fedora CoreOS as a basic hypervisor

We wanted to leverage all the cool Fedora CoreOS features to have a
basic libvirt hypervisor to run our local VMs.
To do so, we created a custom `butane` configuration to include the
libvirt packages and some other goodies such as:

* Allow the `core` user to run virsh commands
* Configure a `baremetal` bridge using NetworkManager files
* Set the default editor to vim
* Configure the timezone
* Disable zincati to avoid rebooting the server when an update is applied
* Adding the Red Hat certificate to the OS trust store
* Create a fancy alias for all users (to run [`kcli`](https://kcli.readthedocs.io/en/latest/) commands in a toolbox container)
* Create a systemd-path to prevent modifications to the `/var/lib/libvirt/images`
folder permissions when updated
* Run a user systemd unit to perform some post installation tasks

## Download the ISO

There are many ways to download the Fedora CoreOS ISO... 
from the more traditional [_use the web_](https://getfedora.org/en/coreos/download) one,
to the fancier one using a container. Let's see the fancier one:

```
$ podman run --privileged --pull=always --rm -v .:/data -w /data \
    quay.io/coreos/coreos-installer:release download -s stable -p metal -f iso

Trying to pull quay.io/coreos/coreos-installer:release...
Getting image source signatures
Copying blob a3ed95caeb02 skipped: already exists  
Copying blob 708557ab4058 done  
Copying blob 1111aecae5c4 done  
Copying blob 6bd970480768 done  
Writing manifest to image destination
Storing signatures
Downloading Fedora CoreOS stable x86_64 metal image (iso) and signature
Read disk 9.3 MiB/760.0 MiB (1%)
...
Read disk 760.0 MiB/760.0 MiB (100%)
gpg: Signature made Tue Feb 15 05:23:46 2022 UTC
gpg:                using RSA key 787EA6AE1147EEE56C40B30CDB4639719867C58F
gpg: checking the trustdb
gpg: marginals needed: 3  completes needed: 1  trust model: pgp
gpg: depth: 0  valid:   4  signed:   0  trust: 0-, 0q, 0n, 0m, 0f, 4u
gpg: Good signature from "Fedora (35) <fedora-35-primary@fedoraproject.org>" [ultimate]
./fedora-coreos-35.20220131.3.0-live.x86_64.iso
```

This will download the ISO in the current folder:

```
$ ls -l fedora*
-rw-r--r--. 1 edu edu 796917760 feb 17 11:40 fedora-coreos-35.20220131.3.0-live.x86_64.iso
-rw-r--r--. 1 edu edu       566 feb 17 11:40 fedora-coreos-35.20220131.3.0-live.x86_64.iso.sig
```

## Create a butane configuration

[Butane](https://coreos.github.io/butane/) is the way to create custom ignition files
to install a Fedora CoreOS system. It is basically a (yet another) yaml file where to
declare user settings, filesystem layout, folder structure, custom systemd units, etc.

The [basic.yaml](basic.yaml) file included shows some of those things in action. The trickier
part is the `rpm-ostree` installation of the overlayed packages, in this case libvirtd and some
other friends. In order to do that, we created a custom systemd unit that runs once and
does the layering automatically... as well as some other stuff required to allow the `core`
user to run virsh commands.

> **NOTE**: There are a few things that probably can be done in a better way in that butane file...

The [butane specificiation](https://coreos.github.io/butane/config-fcos-v1_4/) and the
[butane examples](https://coreos.github.io/butane/examples/) explain in good detail all the
things you can do with it. Also, check the
[Fedora CoreOS documentation](https://docs.fedoraproject.org/en-US/fedora-coreos/producing-ign/)
for more examples.

## Convert the butane configuration file to ignition

Once we are confortable with the butane configuration, it is time to convert it to a igntion file
for Fedora CoreOS to understand. As well as downloading the ISO, there are many ways to do it, from
downloading the `butane` binary from github, installing it with a traditional package manager or
from a container:

```
$ podman run --interactive --rm quay.io/coreos/butane:release \
       --pretty --strict < your_config.butane > my.ign
```

## Host the ignition file _somewhere_

The Fedora CoreOS installation process requires the ignition file to be hosted somewhere. Again,
multiple choices: embed it in the ISO or be reachable over the network.

In this case, a simple http server will serve the ignition file:

```
$ podman run -dt -v ${PWD}:/var/www/html:Z --name webserver \
  -p 8080:8080 registry.centos.org/centos/httpd-24-centos7:latest
```

The ignition file should be reachable at `http://IP:8080/my.ign` (check your firewall otherwise)

## Boot the installation

We mapped the ISO as a `virtual media` device in the baremetal host and booted from there. To do so,
we hosted the ISO in the same http server than the ignition configuration and used RedFish to map it
as a virtual media:

```
$ export username_password='USER:PASSWORD'

# Eject Media
$ curl -L -ku ${username_password} -H "Content-Type: application/json" \
  -H "Accept: application/json" -d '{}' \
  -X POST https://$BMC_ADDRESS/redfish/v1/Managers/Self/VirtualMedia/1/Actions/VirtualMedia.EjectMedia

# Media Status
$ curl -L -ku ${username_password} -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -X GET https://$BMC_ADDRESS/redfish/v1/Managers/Self/VirtualMedia/1 | python -m json.tool

# Insert Media. Please use your http server and iso file
$ curl -L -ku ${username_password} -H "Content-Type: application/json" \
  -H "Accept: application/json" -d '{"Image": "http://IP:8080/my.iso"}' \
  -X POST https://$BMC_ADDRESS/redfish/v1/Managers/Self/VirtualMedia/1/Actions/VirtualMedia.InsertMedia

# Set boot order
$ curl --globoff  -L -w "%{http_code} %{url_effective}\\n" -ku ${username_password} \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{"Boot":{ "BootSourceOverrideEnabled": "Once", "BootSourceOverrideTarget": "Cd", "BootSourceOverrideMode": "UEFI"}}' \
  -X PATCH http://$BMC_ADDRESS/redfish/v1/Systems/Self

# Poweroff
$ curl -L -ku ${username_password} -H "Content-Type: application/json" \
  -H "Accept: application/json" -d '{"ResetType": "ForceOff"}' \
  -X POST https://$BMC_ADDRESS/redfish/v1/Systems/1/Actions/ComputerSystem.Reset

# Poweron
$ curl -L -ku ${username_password} -H "Content-Type: application/json" \
  -H "Accept: application/json" -d '{"ResetType": "On"}' \
  -X POST https://$BMC_ADDRESS/redfish/v1/Systems/1/Actions/ComputerSystem.Reset
```

Or if using SuperMicro (using the [`sum`](https://www.supermicro.com/en/solutions/management-software/supermicro-update-manager) tool):

```
# Mount the ISO
$ sum -i ${HOST} -u ${USER} -p ${PASSWORD} -c MountIsoImage --image_url=${URL} > /dev/null

# Boot once VirtualCD
$ curl -s --globoff -L -w "%{http_code} %{url_effective}\\n" -ku ${USER}:${PASSWORD} \
  -H "Content-Type: application/json" -H "Accept: application/json" \
  -d '{"Boot":{ "BootSourceOverrideEnabled": "Once", "BootSourceOverrideTarget": "UsbCd"}}' \
  -X PATCH https://${HOST}/redfish/v1/Systems/1

# Reboot
$ sum -i ${HOST} -u ${USER} -p ${PASSWORD} -c SetPowerAction --action reset > /dev/null
```

> **WARNING**: It is mandatory if using SuperMicro that the url where the ISO is hosted to have a 'path' such as http://IP_OR_HOSTNAME/somepath/MY.ISO otherwise it will fail.

## Install Fedora CoreOS

After the system is already booted, you just need to run the `coreos-installer` tool as:

```
$ sudo coreos-installer install /dev/sda \
  --ignition-url http://IP:8080/my.ign --insecure-ignition
$ sudo reboot
```

Once the system is rebooted, the Fedora CoreOS final system will be booted and ignition will perform
the changes required.

Once it finishes, the system is ready to be used!

> **NOTE**: Embeding the ignition file into the ISO would skip this step.

## Post install workarounds

After all the post-installation tasks, a reboot is required:

```
$ sudo reboot
```

## To Do

* [Reboot once post ignition?](https://discussion.fedoraproject.org/t/reboot-once-post-ignition-in-fedora-coreos/37107)
* [Nested directories issue?](https://discussion.fedoraproject.org/t/fedora-coreos-ignition-nested-directories-and-permissions-issue/37010)
* [Why creating a folder in `/etc/skel` via ignition is ignored for the `core` user?](https://discussion.fedoraproject.org/t/etc-skel-not-used-for-core-user-in-fedora-coreos/36973)