#!/bin/bash

if [ ! -d /var/log/diamond ]; then
    mkdir /var/log/diamond
fi

# Launch Diamond
exec /usr/local/bin/diamond -f --skip-change-user --skip-fork -c /etc/diamond/diamond.conf
