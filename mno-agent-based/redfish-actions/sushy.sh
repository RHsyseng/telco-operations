#! /usr/bin/env bash

media_insert(){
    curl -k -s --noproxy "*"  -w "%{http_code} %{url_effective}\\n"  -L --globoff -H "Content-Type: application/json" -H "Accept: application/json" \
    -d "{\"Image\": \"${2}\"}" \
    -X POST "${1/Systems/Managers}"/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia
}

media_eject() {
    curl -k -s --noproxy "*" --globoff -L -w "%{http_code} %{url_effective}\\n"  \
    -d '{}'  -X POST "${1/Systems/Managers}"/VirtualMedia/Cd/Actions/VirtualMedia.EjectMedia
}

boot_once() {
  echo "no op for virt"
}

power_on(){
    curl -k -s --noproxy "*" --globoff -L -w "%{http_code} %{url_effective}\\n"  \
    -H "Content-Type: application/json" -H "Accept: application/json" \
    -d '{"ResetType": "On"}' \
    -X POST "$1"/Actions/ComputerSystem.Reset
}

power_off(){
    curl -k -s --noproxy "*" --globoff -L -w "%{http_code} %{url_effective}\\n"  \
    -H "Content-Type: application/json" -H "Accept: application/json" \
    -d '{"ResetType": "ForceOff"}' \
    -X POST "$1"/Actions/ComputerSystem.Reset
}
