#!/bin/bash

# Docker with confd to manage the configuration
# see https://github.com/kelseyhightower/confd/blob/master/docs/quick-start-guide.md

IMAGE=diamond-ontapclustercollector

# 1. Build the docker image
docker build -t $IMAGE .

# 2. Run the image
# First, define the ETCD/Consul keys for the configuration 
# (if you are using coreos, for example)

## A handler is active, if its folder exists.
## Archive handler
#etcdctl set /diamond/handler/archive/file '/var/log/diamond/archive.log'
#etcdctl set /diamond/handler/archive/days '1'
## Graphite handler
##etcdctl set /diamond/handler/graphite/host 'localhost'
##etcdctl set /diamond/handler/graphite/port '2004'
## GraphitePickle handler
##etcdctl set /diamond/handler/graphitepickle/host 'localhost'
##etcdctl set /diamond/handler/graphitepickle/port '2004'
##etcdctl set /diamond/handler/graphitepickle/batch '512'
## Diamond default for collectors
##etcdctl set /diamond/collectors/hostname 'docker1'
##etcdctl set /diamond/collectors/pathprefix 'servers'
##etcdctl set /diamond/collectors/pathsuffix
##etcdctl set /diamond/collectors/instanceprefix
##etcdctl set /diamond/collectors/interval
## Add OntapClusterCollector keys to etcd
#etcdctl set /diamond/collectors/ontapclustercollector/enabled 'True'
#etcdctl set /diamond/collectors/ontapclustercollector/pathprefix 'netapp'
#etcdctl set /diamond/collectors/ontapclustercollector/interval '45'
## NetApp devices
#etcdctl set /diamond/collectors/ontapclustercollector/devices/netapp1/user 'root'
#etcdctl set /diamond/collectors/ontapclustercollector/devices/netapp1/password 'root'
#etcdctl set /diamond/collectors/ontapclustercollector/devices/netapp1/ip '10.0.0.1'
#etcdctl set /diamond/collectors/ontapclustercollector/devices/netapp1/publish '1'

# Otherwise, define the environemnt variables
# Archive handler
DIAMOND_HANDLER_ARCHIVE='ArchiveHandler'  # whatever value, just not empty
DIAMOND_HANDLER_ARCHIVE_FILE='/var/log/diamond/archive.log'
DIAMOND_HANDLER_ARCHIVE_DAYS='1'
# Graphite handler
#DIAMOND_HANDLER_GRAPHITE_HOST='localhost'
# Add OntapClusterCollector keys to etcd
DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_ENABLED='True'
DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_PATHPREFIX='netapp'
# NetApp devices
DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_DEVICES="netapp1" # whatever value!
DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_DEVICES_NETAPP1_USER='root'
DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_DEVICES_NETAPP1_PASSWORD='root'
DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_DEVICES_NETAPP1_IP='10.0.0.1'

# Run it!
docker run -i -t \
-e DIAMOND_HANDLER_ARCHIVE=$DIAMOND_HANDLER_ARCHIVE \
-e DIAMOND_HANDLER_ARCHIVE_FILE=$DIAMOND_HANDLER_ARCHIVE_FILE \
-e DIAMOND_HANDLER_ARCHIVE_DAYS=$DIAMOND_HANDLER_ARCHIVE_DAYS \
-e DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_ENABLED=$DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_ENABLED \
-e DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_PATHPREFIX=$DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_PATHPREFIX \
-e DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_DEVICES=$DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_DEVICES \
-e DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_DEVICES_NETAPP1_USER=$DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_DEVICES_NETAPP1_USER \
-e DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_DEVICES_NETAPP1_PASSWORD=$DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_DEVICES_NETAPP1_PASSWORD \
-e DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_DEVICES_NETAPP1_IP=$DIAMOND_COLLECTORS_ONTAPCLUSTERCOLLECTOR_DEVICES_NETAPP1_IP \
$IMAGE "$@"

