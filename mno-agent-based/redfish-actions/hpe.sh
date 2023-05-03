#! /usr/bin/env bash

media_insert(){
  curl -k -s --noproxy "*" -u "$AUTH" -w "%{http_code} %{url_effective}\\n" -L --globoff -H "Content-Type: application/json" -H "Accept: application/json" \
    -d "{\"Image\": \"${2}\", \"Inserted\":true, \"WriteProtected\":true}" \
    -X POST "$1"/redfish/v1/Managers/1/VirtualMedia/2/Actions/VirtualMedia.InsertMedia
}

media_eject() {
  curl -k -s --noproxy "*" -u "$AUTH" -w "%{http_code} %{url_effective}\\n" -L --globoff -H "Content-Type: application/json" -H "Accept: application/json" \
    -d '{}' \
    -X POST "$1"/redfish/v1/Managers/1/VirtualMedia/2/Actions/VirtualMedia.EjectMedia
}

media_status(){
  curl -k -s --noproxy "*" -u "$AUTH" -L --globoff -H "Content-Type: application/json" -H "Accept: application/json" \
    -X GET "${1}/redfish/v1/Managers/1/VirtualMedia/2" | jq
}


boot_once() {
  curl -k -s --noproxy "*" -u "$AUTH" -w "%{http_code} %{url_effective}\\n" -L --globoff -H "Content-Type: application/json" -H "Accept: application/json" \
    -d '{"Boot":{ "BootSourceOverrideEnabled": "Once", "BootSourceOverrideTarget": "Cd"}}' \
    -X PATCH "$1"/redfish/v1/Systems/1
}

power_on(){
  curl -k -s --noproxy "*" -u "$AUTH" -w "%{http_code} %{url_effective}\\n" -L --globoff -H "Content-Type: application/json" -H "Accept: application/json" \
    -d '{"ResetType": "On"}' \
    -X POST "$1"/redfish/v1/Systems/1/Actions/ComputerSystem.Reset
}

power_off(){
  curl -k -s --noproxy "*" -u "$AUTH" -w "%{http_code} %{url_effective}\\n" -L --globoff -H "Content-Type: application/json" -H "Accept: application/json" \
    -d '{"ResetType": "ForceOff"}' \
    -X POST "$1"/redfish/v1/Systems/1/Actions/ComputerSystem.Reset
}

bios_status(){
  curl -k -s --noproxy "*" -u "$AUTH" -w "%{http_code} %{url_effective}\\n" -L --globoff -H "Content-Type: application/json" -H "Accept: application/json" \
    -X GET "$1"/redfish/v1/Systems/1/Bios
}
