# diamond-ontap collector for graphite

About OntapClusterCollector
===========================

OntapClusterCollector is a diamond plugin to collect metrics from a NetApp 
Ontap OS 7-Mode or/and C-Mode (Cluster Mode) using the NetApp Manageability 
SDK.

It is not only a plugin, it is also a standalone program to check the 
performance objects on NetApp.


```
$ ./ontapng.py  --help
Standalone program and/or Diamond plugin to retrive metrics
and info from NetApp devices. It supports 7-Mode anc C-Mode.
Usage:

    ./ontapng.py [-h | --help]
    ./ontapng.py -s <server> -u <user> -p <password> [action]

Where <action> could be:

 * objects : returns all objects available on the device
 * info <object> : returns all metrics for <object>
 * instances <object> : returns the name of all instaces of <object>
 * metrics <object> [instace]: returns all counters for all instances
   or if one instances is provided, only for that one.

(c) Jose Riguera Lopez, November 2003
<jose.riguera@springer.com>
    
```

SDK
===

In order to get working these modules, you will need the SDK on the system. 
This module has been developed using v5.0 of the SDK. As of writing the SDK 
can be found at https://communities.netapp.com/docs/DOC-1152


About Diamond
=============

Diamond is a python daemon that collects system metrics and publishes them to
[Graphite](https://github.com/BrightcoveOS/Diamond/wiki/handler-GraphiteHandler)
(and [others](https://github.com/BrightcoveOS/Diamond/wiki/Handlers)). It is
capable of collecting cpu, memory, network, i/o, load and disk metrics.  
Additionally, it features an API for implementing custom collectors for 
gathering metrics from almost any source.

Diamond collectors run within the diamond process and collect metrics that can 
be published to a graphite server.


Configuration 
=============

The NetAPP python API is bundled with the collector.

Example OntapClusterCollector.conf:
```
# Configuration for OntapClusterCollector

enabled = True
path_prefix = netapp
reconnect = 60
hostname_method = none
method = Threaded
splay = 20

[devices]

#    [[cluster]]
#    ip = 123.123.123.123
#    user = root
#    password = strongpassword
#    publish = 1   # 1 = publish all metrics
#                  # 2 = do not publish zeros
#                  # 0 = do not publish
#
#        #[[[na_object=pretty.path.@.${metric1}|filters]]]
#        # This is the list of metrics to collect.
#        # The na_object is the object name in the NetApp API.
#        # For each object we have a list of metrics to retrieve.
#        # The purpose of the pretty name is to enable replacement of reported
#        # metric names, since some the names in the API can be confusing.
#
#        [[[aggregate=${node_name}.aggr.$instance_name]]]
#        total_transfers = rate_ops
#        user_reads = rate_ops_reads
#        user_writes = rate_ops_writes
#        cp_reads = -
#
	[[cluster]]
        ip = 10.3.3.176
        user = admin
        password = password
        publish = 1

                [[[aggregate=nodes.${node_name}.aggr.${instance_name}]]]
                total_transfers = rate_ops
                user_reads = rate_ops_reads
                user_writes = rate_ops_writes
                cp_reads = rate_ops_cp_reads
                user_read_blocks = rate_blocks_user_reads
                user_write_blocks = rate_blocks_user_writes
                cp_read_blocks = rate_blocks_cp_reads
                wv_fsinfo_blks_used = blocks_used
                wv_fsinfo_blks_total = blocks_total

                [[[disk=nodes.${node_name}.aggr.${raid_group}.${instance_name}]]]
                disk_speed = rpm
                total_transfers = rate_iops
                user_reads = rate_ops_reads
                user_writes = rate_ops_writes
                cp_reads = rate_read_cp
                disk_busy = pct_busy
                io_pending = avg_iops_pending
                io_queued = avg_iops_queued
                user_write_blocks = rate_blocks_write
                user_write_latency = avg_latency_micros_write
                user_read_blocks = rate_blocks_read
                user_read_latency = avg_latency_micros_read
                cp_read_blocks = rate_blocks_cp_read
                cp_read_latency = avg_latency_micros_cp_read

                [[[processor=nodes.${node_name}.processor.${instance_name}]]]
                processor_busy = pct_busy
                processor_elapsed_time = time_elapsed
                domain_busy = -
        
		# ...

        [[sever-mode]]
        ip = 172.29.1.161
        user = root
        password = password
        publish = 1

                [[[aggregate=aggregate.@]]]
                total_transfers = rate_ops
                user_reads = rate_ops_reads
                user_writes = rate_ops_writes
                cp_reads = rate_ops_cp_reads
                user_read_blocks = rate_blocks_user_reads
                user_write_blocks = rate_blocks_user_writes
                cp_read_blocks = rate_blocks_cp_reads
                wv_fsinfo_blks_used = blocks_used
                wv_fsinfo_blks_total = blocks_total

                [[[processor=processor.@]]]
                processor_busy = pct_busy
                processor_elapsed_time = time_elapsed
                domain_busy = -

                [[[system=@]]]
                nfs_ops = rate_ops_nfs
                cifs_ops = rate_ops_cifs
                fcp_ops = rate_ops_fcp
                iscsi_ops = rate_ops_iscsi
                read_ops = rate_ops_read
                write_ops = rate_ops_write
                sys_write_latency = avg_latency_ms_write
                sys_read_latency = avg_latency_ms_read
                total_ops = rate_ops
                sys_avg_latency = avg_latency_ms
                net_data_recv = rate_kbytes_net_recv
                net_data_sent = rate_kbytes_net_sent
                fcp_data_recv = rate_kbytes_fcp_recv
                fcp_data_sent = rate_kbytes_fcp_sent
                disk_data_read = rate_kbytes_disk_read

                # ...
```


Installation and requirements
=============================

To run this collector in test mode you can invoke the diamond server with the
-r option and specify the collector path.

```
diamond -f -r path/to/ontapng.py -c conf/diamond.conf
```

running diamond in the foreground (-f) while logging to stdout (-l) is a good way to quickly see if a custom collector is unable to load.

```
diamond -f -l
```


# Author

Author:: Jose Riguera López (Springer SBM) (<jose.riguera@springer.com>)
