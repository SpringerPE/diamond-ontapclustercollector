#!/bin/bash

if [ ! -z "$CONFD_BIN" ] && [ -x "$CONFD_BIN" ]; then
   ETCD_PORT=${ETCD_PORT:-4001}
   ETCD_HOST=${ETCD_HOST:-10.1.42.1}

   # Check if the ETCD host:port is open
   exec 6<>/dev/tcp/$ETCD_HOST/$ETCD_PORT
   RESULT=$?
   exec 6>&- # close output connection
   exec 6<&- # close input connection

   if [ $RESULT == 0 ]; then
      # Run confd in the background to watch the upstream servers
      exec $CONFD_BIN -node "http://$ETCD_HOST:$ETCD_PORT"
   else
      # Run confd in the background to watch the upstream servers
      exec $CONFD_BIN -backend env
   fi
fi
exec true
