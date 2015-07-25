About OntapClusterCollector
===========================

OntapClusterCollector is a diamond plugin to collect metrics from a NetApp 
Ontap OS 7-Mode or/and C-Mode (Cluster Mode) using the NetApp Manageability 
SDK. It is smart enought to work out the dependencies to gather a specific 
metric, and also calculate the value depending if it is a delta, a rate, 
a derivative metric or a "second" derivative metric.

It is not only a plugin, it is also a standalone program to see and check the 
performance objects on NetApp. 

```
$ ./ontapng.py  --help
Standalone program and/or Diamond plugin to retrive metrics
and info from NetApp devices. It supports 7-Mode anc C-Mode.
Usage:

    ./ontapng.py [-h | --help]
    ./ontapng.py [-v <api.version>] -s <server> -u <user> -p <password> [action]

Where <action> could be:

 * objects : returns all objects available on the device
 * info <object> : returns all metrics for <object>
 * instances <object> : returns the name of all instaces of <object>
 * metrics <object> [instace]: returns all counters for all instances
   or if one instances is provided, only for that one.

(c) Jose Riguera Lopez, 2013-2015 <jose.riguera@springer.com>
    
```

SDK
===

In order to get working these modules, you will need the SDK on the system. 
This module has been developed using v5.0 of the SDK. As of writing the SDK 
can be found at https://communities.netapp.com/docs/DOC-1152


About Diamond
=============

Diamond is a python daemon that collects system metrics and publishes them to
[Graphite](https://github.com/python-diamond/Diamond/wiki/handler-GraphitePickleHandler)
(and [others](https://github.com/python-diamond/Diamond/wiki/Handlers)). It is
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
splay = 10
interval = 50  # Could be 60 ... but just to avoid gaps

[devices]

#    [[cluster]]
#    ip = 123.123.123.123
#    user = root
#    password = strongpassword
#    apiversion = 1.15
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
        apiversion = 1.15

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

                [[[system=nodes.${node_name}.${instance_name}]]]
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
                disk_data_written = rate_kbytes_disk_written
                cpu_busy = pct_cpu_busy
                cpu_elapsed_time = base_time_cpu_elapsed
                avg_processor_busy = pct_processors_all_avg_busy
                cpu_elapsed_time1 = base_time_cpu_elapsed_avg
                total_processor_busy = pct_processors_all_total_busy
                cpu_elapsed_time2 = base_time_cpu_elapsed_total

                [[[ifnet=nodes.${node_name}.net.${instance_name}]]]
                recv_packets = rate_pkts_recv
                recv_errors = rate_recv_errors
                send_packets = rate_pkts_send
                send_errors = rate_send_errors
                collisions = rate_collisions
                recv_drop_packets = rate_pkts_drop
                recv_data = rate_bytes_recv
                send_data = rate_bytes_send

                [[[ext_cache_obj=nodes.${node_name}.ext_cache.${instance_name}]]]
                usage = pct_usage_blocks
                accesses = cnt_delta_accesses
                blocks = cnt_blocks
                disk_reads_replaced = rate_disk_replaced_readio
                hit = rate_hit_buffers
                hit_flushq = rate_flushq_hit_buffers
                hit_once = rate_once_hit_buffers
                hit_age = rate_age_hit_buffers
                miss = rate_miss_buffers
                miss_flushq = rate_flushq_miss_buffers
                miss_once = rate_once_miss_buffers
                miss_age = rate_age_miss_buffers
                hit_percent = pct_hit
                inserts = rate_inserts_buffers
                inserts_flushq = rate_flushq_inserts_buffers
                inserts_once = rate_once_inserts_buffers
                inserts_age = rate_age_inserts_buffers
                reuse_percent = pct_reuse
                evicts = rate_evicts_blocks
                evicts_ref = rate_ref_evicts_blocks
                invalidates = rate_invalidates_blocks

                [[[wafl=nodes.${node_name}.${instance_name}]]]
                name_cache_hit = rate_cache_hits
                total_cp_msecs = cnt_msecs_spent_cp
                wafl_total_blk_writes = rate_blocks_written
                wafl_total_blk_readaheads = rate_blocks_readaheads
                wafl_total_blk_reads = rate_blocks_read

                [[[volume=vservers.${vserver_name}.volumes.${instance_name}]]]
                total_ops = rate_ops
                read_ops = rate_ops_read
                write_ops = rate_ops_write
                other_ops = rate_ops_other
                avg_latency = avg_latency_micros
                read_blocks = rate_blocks_read
                write_blocks = rate_blocks_write
                read_latency = avg_latency_micros_read
                write_latency = avg_latency_micros_write
                read_data = rate_bytes_read
                write_data = rate_bytes_write
                other_latency = avg_latency_micros_other
                wv_fsinfo_blks_total = cnt_blocks_total
                wv_fsinfo_blks_reserve = cnt_blocks_reserved
                wv_fsinfo_blks_used = cnt_blocks_used

                [[[nfsv3=vservers.${instance_name}.nfsv3]]]
                nfsv3_ops = rate_ops_nfsv3
                nfsv3_read_ops = rate_ops_nfsv3_read
                nfsv3_write_ops = rate_ops_nfsv3_write
                read_total = cnt_ops_read
                write_total = cnt_ops_write
                write_avg_latency = avg_latency_micros_nfsv3_write
                read_avg_latency = avg_latency_micros_nfsv3_read
                nfsv3_write_throughput = rate_throughput_nfsv3_write
                nfsv3_read_throughput = rate_throughput_nfsv3_read
                nfsv3_throughput = rate_throughput_nfsv3
                nfsv3_dnfs_ops = rate_ops_nfsv3_oracle

                [[[iscsi_lif:vserver=vservers.${instance_name}.iscsi]]]
                iscsi_read_ops = rate_ops_iscsi_read
                iscsi_write_ops = rate_ops_iscsi_write
                avg_write_latency = avg_latency_micros_iscsi_write
                avg_read_latency = avg_latency_micros_iscsi_read
                avg_latency = avg_latency_micros_iscsi
                data_in_sent = cnt_blocks_recv
                data_out_blocks = cnt_blocks_sent

                [[[cifs=vservers.${instance_name}.cifs]]]
                cifs_ops = rate_ops_cifs
                cifs_read_ops = rate_ops_cifs_read
                cifs_write_ops = rate_ops_cifs_write
                cifs_latency = avg_latency_micros_cifs
                cifs_write_latency = avg_latency_micros_cifs_write
                cifs_read_latency = avg_latency_micros_cifs_read
                connected_shares = cnt_cifs_connected_shares
                reconnection_requests_total = cnt_cifs_reconnection_requests_total


        [[sever-mode]]
        ip = 172.29.1.161
        user = root
        password = password
        publish = 1
        apiversion = 1.12

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
                #domain_busy = -

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
                disk_data_written = rate_kbytes_disk_written
                cpu_busy = pct_cpu_busy
                cpu_elapsed_time = base_time_cpu_elapsed
                avg_processor_busy = pct_processors_all_avg_busy
                cpu_elapsed_time1 = base_time_cpu_elapsed_avg
                total_processor_busy = pct_processors_all_total_busy
                cpu_elapsed_time2 = base_time_cpu_elapsed_total

                [[[disk=disk.${raid_name}]]]
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

                [[[ifnet=net.@]]]
                recv_packets = rate_pkts_recv
                recv_errors = rate_recv_errors
                send_packets = rate_pkts_send
                send_errors = rate_send_errors
                collisions = rate_collisions
                recv_drop_packets = rate_pkts_drop
                recv_data = rate_bytes_recv
                send_data = rate_bytes_send

                [[[ext_cache_obj=ext_cache.@]]]
                usage = pct_usage_blocks
                accesses = cnt_delta_accesses
                blocks = cnt_blocks
                disk_reads_replaced = rate_disk_replaced_readio
                hit = rate_hit_buffers
                hit_flushq = rate_flushq_hit_buffers
                hit_once = rate_once_hit_buffers
                hit_age = rate_age_hit_buffers
                miss = rate_miss_buffers
                miss_flushq = rate_flushq_miss_buffers
                miss_once = rate_once_miss_buffers
                miss_age = rate_age_miss_buffers
                hit_percent = pct_hit
                inserts = rate_inserts_buffers
                inserts_flushq = rate_flushq_inserts_buffers
                inserts_once = rate_once_inserts_buffers
                inserts_age = rate_age_inserts_buffers
                reuse_percent = pct_reuse
                evicts = rate_evicts_blocks
                evicts_ref = rate_ref_evicts_blocks
                invalidates = rate_invalidates_blocks

                [[[wafl=@]]]
                name_cache_hit = rate_cache_hits
                total_cp_msecs = cnt_msecs_spent_cp
                wafl_total_blk_writes = rate_blocks_written
                wafl_total_blk_readaheads = rate_blocks_readaheads
                wafl_total_blk_reads = rate_blocks_read

                [[[volume=volume.@]]]
                total_ops = rate_ops
                read_ops = rate_ops_read
                write_ops = rate_ops_write
                other_ops = rate_ops_other
                avg_latency = avg_latency_micros
                read_blocks = rate_blocks_read
                write_blocks = rate_blocks_write
                read_latency = avg_latency_micros_read
                write_latency = avg_latency_micros_write
                read_data = rate_bytes_read
                write_data = rate_bytes_write
                other_latency = avg_latency_micros_other
                wv_fsinfo_blks_total = cnt_blocks_total
                wv_fsinfo_blks_reserve = cnt_blocks_reserved
                wv_fsinfo_blks_used = cnt_blocks_used

                [[[nfsv3=nfsv3.@]]]
                nfsv3_ops = rate_ops_nfsv3
                nfsv3_read_ops = rate_ops_nfsv3_read
                nfsv3_write_ops = rate_ops_nfsv3_write
                nfsv3_avg_write_latency_base = cnt_base_latency_nfsv3_avg_write
                nfsv3_write_latency = avg_latency_ms_nfsv3_write
                nfsv3_avg_read_latency_base = cnt_base_latency_nfsv3_avg_read
                nfsv3_read_latency = avg_latency_ms_nfsv3_read
                nfsv3_op_count = cnt_ops_null, cnt_ops_getattr, cnt_ops_setattr, cnt_ops_lookup, cnt_ops_access, cnt_ops_readlink, cnt_ops_read, cnt_ops_write, cnt_ops_create, cnt_ops_mkdir, cnt_ops_symlink, cnt_ops_mknod, cnt_ops_remove, cnt_ops_rmdir, cnt_ops_rename, cnt_ops_link, cnt_ops_readdir, cnt_ops_readdirplus, cnt_ops_fsstat, cnt_ops_fsinfo, cnt_ops_pathconf, cnt_ops_commit
                nfsv3_op_percent = pct_ops_null, pct_ops_getattr, pct_ops_setattr, pct_ops_lookup, pct_ops_access, pct_ops_readlink, pct_ops_read, pct_ops_write, pct_ops_create, pct_ops_mkdir, pct_ops_symlink, pct_ops_mknod, pct_ops_remove, pct_ops_rmdir, pct_ops_rename, pct_ops_link, pct_ops_readdir, pct_ops_readdirplus, pct_ops_fsstat, pct_ops_fsinfo, pct_ops_pathconf, pct_ops_commit

                [[[cifs=cifs.@]]]
                cifs_ops = rate_ops
                cifs_op_count = cnt_delta_ops
                cifs_read_ops = rate_ops_read
                cifs_write_ops = rate_ops_write
                cifs_latency = avg_latency_ms
                cifs_write_latency = avg_latency_ms_writes
                cifs_read_latency = avg_latency_ms_reads

```

The format for each object is `[[[OBJECT-TYPE=PRETTY.PATH]]]`, where `OBJECT-TYPE` is a type 
of object available on the device. `PRETTY.PATH` is a string to tell the program how build the 
parent path for all the metrics for each OBJECT-TYPE instance found. To see all the object's 
type, instances and metrics just use the command line feature. This is the definition format:
* `fixed.path.string`: just a static path to include in all instances.
* `@` special variable to point to instance name reported by the API.
* `${metric}`: reference to a metric available on the instance. A difference with the rest of the metrics,
   this one can be a string, in that case you cannot reference it on the list of the metrics to gather.

To specify the list of metrics to be gather per OBJECT-TYPE instance, the format is easy:

* `NetApp_api_metric = pretty_name`, meaning that it will rewrite the API metric name to `pretty_name` and send it to the handler.
* `NetApp_api_array_metric = pretty_name1, pretty_name2 ...`, it does the same but for each metric in an array.
* `NetApp_api_array_metric = -` it will not rewrite the names, it will use the ones provided by the API.


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

Also, if you want to use Docker container to run the collector, have a look at the `docker.sh` about howto build it, run it
and pass the variables to define the configuration file.


# Author

Author:: Jose Riguera López (Springer SBM) (<jose.riguera@springer.com>)
