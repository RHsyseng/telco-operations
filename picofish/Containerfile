FROM python:3.9-slim-bullseye

MAINTAINER Karim Boumedhel <karimboumedhel@gmail.com>

LABEL name="rhsysdeseng/picofish" \
      maintainer="karimboumedhel@gmail.com" \
      vendor="Telcops" \
      version="latest" \
      release="0" \
      summary="Workaround supermicro redfish bugs" \
      description="Workaround supermicro redfish bugs"

RUN echo 'APT::Install-Recommends "0";' >> /etc/apt/apt.conf && echo 'APT::Install-Suggests "0";' >> /etc/apt/apt.conf && apt-get update && apt-get -y install python3-flask python3-openssl python3-requests && apt -y autoremove && apt-get clean all
ADD picofish.py /

CMD [ "/usr/bin/python3", "-u", "/picofish.py" ]
