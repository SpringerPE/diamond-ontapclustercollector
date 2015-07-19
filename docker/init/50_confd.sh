#!/bin/bash -e

if [ ! -z "$CONFD_BIN" ] && [ -x "$CONFD_BIN" ]; then
   ETCD_PORT=${ETCD_PORT:-4001}
   ETCD_HOST=${ETCD_HOST:-10.1.42.1}

   # Check if the ETCD host:port is open
   exec 6<>/dev/tcp/$ETCD_HOST/$ETCD_PORT
   RESULT=$?
   exec 6>&- # close output connection
   exec 6<&- # close input connection

   if [ $RESULT == 0 ]; then
      # Loop until confd has updated the configs
      until $CONFD_BIN -onetime -node "http://$ETCD_HOST:$ETCD_PORT"; do
         sleep 2
      done
   else
      # Loop until confd has updated the configs
      until $CONFD_BIN -onetime -backend env; do
         sleep 2
      done
   fi
fi

