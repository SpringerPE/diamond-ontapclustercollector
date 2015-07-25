#!/bin/bash

function alarm() {
    local timeout=$1; shift;
    bash -c "$@" &
    local pid=$!
    {
      sleep $timeout
      kill $pid 2> /dev/null
    } &
    wait $pid 2> /dev/null
    return $?
}

if command -v confd >/dev/null 2>&1; then
   ETCD_PORT=${ETCD_PORT:-4001}
   ETCD_HOST=${ETCD_HOST:-10.1.42.1}

   # Check if the ETCD host:port is open
   alarm 3 "echo > /dev/tcp/$ETCD_HOST/$ETCD_PORT"
   RESULT=$?

   if [ $RESULT == 0 ]; then
      # Loop until confd has updated the configs
      until confd -onetime -node "http://$ETCD_HOST:$ETCD_PORT"; do
         sleep 2
      done
   else
      # Loop until confd has updated the configs
      until confd -onetime -backend env; do
         sleep 2
      done
   fi
fi

