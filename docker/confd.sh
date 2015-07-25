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
   #exec 6<>/dev/tcp/$ETCD_HOST/$ETCD_PORT
   #RESULT=$?
   #exec 6>&- # close output connection
   #exec 6<&- # close input connection
   alarm 3 "echo > /dev/tcp/$ETCD_HOST/$ETCD_PORT"
   RESULT=$?

   if [ $RESULT == 0 ]; then
      # Run confd in the background to watch the upstream servers
      exec confd -node "http://$ETCD_HOST:$ETCD_PORT"
   else
      # Run confd in the background to watch the upstream servers
      exec confd -backend env
   fi
fi
exec true
