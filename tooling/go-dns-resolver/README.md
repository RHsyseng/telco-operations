# Go DNS Resolver

This simple app was used to check how many DNS resolutions are lost when cluster's CoreDNS is restarted. User can configure how aggressive the DNS resolutions will be, that way we can simulate heavily DNS dependent apps or not that heavy ones.

There is a container image with the built app published at `quay.io/mavazque/dnsresolv:latest`.

## How to use it

There are four env vars you can use to tune the behavior:

* APP_PORT: Where the metrics endpoint will listen (used to check metrics around dns resolution). Default value is `9999`.
* RESOLV_ROUTINES: How many parallel resolutions are executed (used to run more/less DNS dependant apps). Default value is `1`.
* RESOLV_DOMAIN: Which domain gets resolved. Default value is `google.com`.
* RESOLV_TIMEOUT: Time we wait before timing out the DNS resolution (in seconds). Default value is `2`.
* WAIT_INTERVAL: Time we wait before DNS resolutions (in seconds). Default value is `2`.

### Example

Run 10 parallel resolutions against google.com and wait 5 seconds between resolutions and check results:

~~~sh
podman run -ti --rm -e RESOLV_ROUTINES=10 -e WAIT_INTERVAL=5 -p 9999:9999 quay.io/mavazque/dnsresolv:latest
~~~

On a different terminal:

~~~sh
curl http://127.0.0.1:9999/metrics
 
# HELP dns_successful_queries Total number of successful dns queries
# TYPE dns_successful_queries counter
dns_successful_queries 30
# HELP dns_unsuccessful_queries Total number of unsuccessful dns queries
# TYPE dns_unsuccessful_queries counter
dns_unsuccessful_queries 0
~~~

## Running it on OCP

You can use the [deploy.yaml](./ocp-manifests/deploy.yaml) to get the DNS test app deployed on your cluster. Once deployed you can use the [check-stats.sh](./ocp-manifests/check-stats.sh) script to gather DNS resolution stats.
