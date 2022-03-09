#!/usr/bin/env python3
# coding=utf-8

from flask import Flask, request, Response, jsonify
import json
import os
import sys
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse
import time
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

app = Flask(__name__)
USERNAME, PASSWORD = os.environ.get('USERNAME', 'ADMIN'), os.environ.get('PASSWORD', 'ADMIN')
AUTH = HTTPBasicAuth(USERNAME, PASSWORD)
endpoint = os.environ.get('HOST')
if endpoint is None:
    print("Missing Mandatory HOST")
    sys.exit(1)
else:
    if endpoint.startswith('http'):
        p = urlparse(endpoint)
        endpoint = p.netloc
    print(f"Using {endpoint} as endpoint")

try:
    app.config.from_object('settings')
    config = app.config
except ImportError:
    config = {'PORT': os.environ.get('PORT', 9000)}

debug = config['DEBUG'] if 'DEBUG' in list(config) else True
port = int(config['PORT']) if 'PORT' in list(config) else 9000


@app.route("/redfish/v1/Managers/1/VM1/CfgCD/Actions/IsoConfig.Mount", methods=["POST"])
def patch_iso(endpoint):
    body = request.get_json()
    image = body['Image']
    p = urlparse(image)
    newbody = {"Host": f"{p.scheme}://{p.netloc}", "Path": p.path}
    resp = requests.post(f"https://{endpoint}/redfish/v1/Managers/1/VM1/CfgCD/Actions/IsoConfig.UnMount", auth=AUTH,
                         json={}, verify=False)
    resp = requests.patch(f"https://{endpoint}/redfish/v1/Managers/1/VM1/CfgCD", auth=AUTH, json=newbody, verify=False)
    resp = requests.post(f"https://{endpoint}/redfish/v1/Managers/1/VM1/CfgCD/Actions/IsoConfig.Mount", auth=AUTH,
                         json={}, verify=False)
    time.sleep(10)
    excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection"]
    headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
    response = Response(resp.content, resp.status_code, headers)
    return response


@app.route("/<path:path>", methods=["GET", "POST", "DELETE", "PATCH", "PUT"])
def proxy(path):
    if request.method == "GET":
        if path == 'redfish/v1/Managers/1/VM1/' or path == 'redfish/v1/Managers/1/VM1':
            data = {"@odata.context": "/redfish/v1/$metadata#VirtualMediaCollection.VirtualMediaCollection",
                    "@odata.id": "/redfish/v1/Managers/1/VM1",
                    "@odata.type": "#VirtualMediaCollection.VirtualMediaCollection",
                    "Description": "Collection of Virtual Media for this System",
                    "Members": [{"@odata.id": "/redfish/v1/Managers/1/VM1/CfgCD"}],
                    "Members@odata.count": 1,
                    "Name": "Virtual Media Collection"
                    }
            response = jsonify(data)
            response.status_code = 201
            return response
        elif path == "redfish/v1/Managers/1/VM1/CfgCD/" or path == "redfish/v1/Managers/1/VM1/CfgCD":
            data = {"@odata.context": "/redfish/v1/$metadata#VirtualMedia.VirtualMedia",
                    "@odata.id": "/redfish/v1/Managers/1/VM1/CfgCD",
                    "@odata.type": "#VirtualMedia.v1_2_0.VirtualMedia",
                    "Actions": {
                        "#VirtualMedia.EjectMedia": {
                            "target": "/redfish/v1/Managers/1/VM1/CfgCD/Actions/IsoConfig.UnMount"
                        },
                        "#VirtualMedia.InsertMedia": {
                            "target": "/redfish/v1/Managers/1/VM1/CfgCD/Actions/IsoConfig.Mount"
                        }
                    },
                    "ConnectedVia": "NotConnected",
                    "Description": "Ocatopic Virtual Media Services Settings",
                    "Id": "CD",
                    "Image": None,
                    "ImageName": None,
                    "Inserted": False,
                    "MediaTypes": [
                        "CD",
                        "DVD"
                    ],
                    "MediaTypes@odata.count": 2,
                    "Name": "Virtual CD",
                    "WriteProtected": None}
            response = jsonify(data)
            response.status_code = 201
            return response
        elif path == "redfish/v1/Systems/1" or path == "redfish/v1/Systems/1/":
            resp = requests.get(f"https://{endpoint}/{path}", auth=AUTH, verify=False)
            data = json.loads(resp.content)
            data['Boot']['BootSourceOverrideTarget@Redfish.AllowableValues'].append('Cd')
            response = jsonify(data)
            response.status_code = 201
            return response
        resp = requests.get(f"https://{endpoint}/{path}", auth=AUTH, verify=False)
        excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection"]
        headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
        response = Response(resp.content, resp.status_code, headers)
        return response
    elif request.method == "POST":
        body = request.get_json()
        resp = requests.post(f"https://{endpoint}/{path}", auth=AUTH, json=body, verify=False)
        excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection"]
        headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
        response = Response(resp.content, resp.status_code, headers)
        return response
    elif request.method == "PATCH":
        body = request.get_json()
        resp = requests.patch(f"https://{endpoint}/{path}", auth=AUTH, json=body, verify=False)
        if 'Boot' in body and 'BootSourceOverrideTarget' in body['Boot']:
            newbody = {"Boot": {"BootSourceOverrideTarget": "UefiUsbCd", "BootSourceOverrideEnabled": "Once"}}
            resp = requests.patch(f"https://{endpoint}/redfish/v1/Systems/1", auth=AUTH, json=newbody, verify=False)
        excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection"]
        headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
        response = Response(resp.content, resp.status_code, headers)
        return response
    elif request.method == "PUT":
        body = request.get_json()
        resp = requests.put(f"https://{endpoint}/{path}", auth=AUTH, json=body, verify=False)
        excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection"]
        headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]
        response = Response(resp.content, resp.status_code, headers)
        return response
    elif request.method == "DELETE":
        resp = requests.delete(f"https://{endpoint}/{path}", auth=AUTH, verify=False).content
        response = Response(resp.content, resp.status_code, headers)
        return response


def run():
    """

    """
    app.run(host='0.0.0.0', port=port, debug=debug, ssl_context='adhoc')


if __name__ == '__main__':
    run()
