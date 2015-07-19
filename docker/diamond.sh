#!/bin/bash

if [ ! -d /var/log/diamond ]; then
    mkdir /var/log/diamond
fi

# Configure OntaClusterCollector
/usr/local/bin/diamond-ontap-configurator.sh add ${NETAPP_HOST} ${NETAPP_IP} ${NETAPP_USER} ${NETAPP_PASSWORD}

# Launch Diamond
exec /usr/local/bin/diamond -f --skip-change-user --skip-fork -c /etc/diamond/diamond.conf
