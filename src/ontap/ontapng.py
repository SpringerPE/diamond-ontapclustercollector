#!/usr/bin/env python
# coding=utf-8
#
# (c) 2013-2015, Jose Riguera Lopez, <jose.riguera@springer.com>
#
# This plugin/program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import time
import re
import unicodedata
# import logging
# import configobj
import os.path
import getopt
import datetime

from collections import namedtuple as NamedTuple
from string import Template

try:
    from diamond.metric import Metric
    from diamond.collector import Collector
except ImportError:
    # workaround to be able to run this script as standalone program
    # Additional workaround to allow this script to act as a library
    Collector = object

try:
    netappsdkpath = os.path.join('lib', 'netapp')
    netappsdkpath = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), netappsdkpath)
    sys.path.append(netappsdkpath)
    import NaServer
    NaServer  # workaround for pyflakes issue #13
except ImportError:
    raise

"""
The OntapClusterCollector collects metric from a NetApp installation using the
NetApp Manageability SDK. This allows access to many metrics not available
via SNMP.

For this to work you'll the SDK available on the system.
This module has been developed using v5.0 of the SDK.
As of writing the SDK can be found at
https://communities.netapp.com/docs/DOC-1152

You'll also need to specify which NetApp instances the collecter should
get data from.

Example OntapClusterCollector.conf:
```
enabled = True
path_prefix = netapp
reconnect = 60
hostname_method = none
splay = 15
interval = 45               # sleep time
http_timeout = 45           # timeout

[devices]

    [[cluster]]
    ip = 123.123.123.123
    user = root
    password = strongpassword
    apiversion = 1.15
    publish = 1   # 1 = publish all metrics
                  # 2 = do not publish zeros
                  # 0 = do not publish

        #[[[na_object=pretty.path.@.${metric1}|filters]]]
        # This is the list of metrics to collect.
        # The na_object is the object name in the NetApp API.
        # For each object we have a list of metrics to retrieve.
        # The purpose of the pretty name is to enable replacement of reported
        # metric names, since some the names in the API can be confusing.

        [[[aggregate=${node_name}.aggr.$instance_name]]]
        total_transfers = rate_ops
        user_reads = rate_ops_reads
        user_writes = rate_ops_writes
        cp_reads = -

````

The primary source for documentation about the API has been
"NetApp unified storage performance management using open interfaces"
https://communities.netapp.com/docs/DOC-1044

"""


class OntapClusterCollector(Collector):

    def __init__(self, *args, **kwargs):
        """Creates a new instance of the Ontap Collector class.

        Returns a OntapCollector instance.
        """
        # Thread safe due to the double dict structure [device][item]
        self.last_values = {}
        self.last_collect_time = {}
        self.connections = {}
        self.reconnects = {}
        self.dev_running = {}
        self.metrics = {}
        super(OntapClusterCollector, self).__init__(*args, **kwargs)


    def get_default_config_help(self):
        """Help text for the collector configuration options.

        Adds the explanation for the specific parameters for this collector.
        """
        config_help = super(
            OntapClusterCollector, self).get_default_config_help()
        config_help.update({
            'reconnect':    'Number of iterations for reconnecting',
            'http_timeout': 'Http Timeout for every connection',
            'path_prefix':  'Prefix for device.instance.metric',
            'interval':     'Interval',
        })
        return config_help


    def get_default_config(self):
        """Creates default base config for the collector (without devices).

        Returns the default config.
        """
        default_config = super(
            OntapClusterCollector, self).get_default_config()
        default_config.update({
            'path_prefix':      'netapp',
            'reconnect':        60,
            'hostname_method':  'none',
            'interval':         60,
            'http_timeout':     30,
            'measure_collector_time': False
        })
        return default_config


    def _connect(self, to=None):
        """Creates a connetion to the device or devices.

        Makes a connection to the NetAPP server if to is specified
        or to configured all servers. Also, it will force a reconnection
        to the server(s) each 'reconnect' times that this function is called.

        Returns the conection(s) to the device or all configured devices.
        """
        if to and to in self.connections:
            counter = self.reconnects[to]
            if counter != 0:
                self.reconnects[to] = counter - 1
                return self.connections[to]

        for device in self.config['devices']:
            # Get Device Config
            c = self.config['devices'][device]
            if to is None or to == device:
                try:
                    server = NetAppMetrics(
                        c['ip'], c['user'], c['password'], c['apiversion'],
                        self.config['http_timeout'])
                    self.reconnects[device] = int(self.config['reconnect'])
                    self.connections[device] = server
                except (KeyError, ValueError) as e:
                    msg = "Incorrect device '%s' configuration: '%s'"
                    self.log.error(msg, device, str(e))
                    raise
                else:
                    self.log.info("Connected to device '%s'", device)
        if to is None:
            return self.connections
        return self.connections[to]


    def __get_metric(self, device, metric, info_metrics, label, publish=True):
        """Maps each kind of metric with a number and work out the label.

        Where:
            metric: netapp name of the metric
            info_metrics: dict indexed by metric with all properties
            label: new label of the metric
            publish: True if it will be published

        Returns a tuple with: (pretty, unit, prop, base, priv, publish)
        """
        (unit, prop, base, priv, desc, labels) = info_metrics[metric]
        if prop.startswith('raw'):
            prop_type = 1
        elif prop.startswith('rate'):
            prop_type = 2
        elif prop.startswith('delta'):
            prop_type = 3
        elif prop.startswith('average'):
            prop_type = 4
        elif prop.startswith('percent'):
            prop_type = 5
        else:
            prop_type = 0
        if label is None:
            pretty = None
        elif label == '' or label == '-':
            if labels:
                pretty = labels
            else:
                pretty = [metric]
        elif labels:
            if isinstance(label, list):
                if len(label) != len(labels):
                    msg = "Not enough names for metric '%s' on '%s'!"
                    self.log.warning(msg, metric, device)
                    pretty = labels
                else:
                    pretty = label
            else:
                msg = "Metric '%s' on '%s' is an array of values!"
                self.log.warning(msg, metric, device)
                pretty = labels
        else:
            pretty = [label]
        return (pretty, unit, prop_type, base, priv, publish)


    def get_metrics(self, device, server):
        """Gets all the type of metrics from the device.

        Parses all items defined in the configuration file and
        fills a dict of metrics for the device.

        Gets all defined type of metrics from the configuration file
        for the device (and also all of the dependent metrics)
        """
        match_var = re.compile(r'\$([\w_-]+)')
        match_var_b = re.compile(r'\${([\w_-]+)}')
        metrics = {}
        counter_metrics = 0
        self.log.info("Parsing metrics for '%s'", device)
        conf = self.config['devices'][device]
        for cobject in conf.keys():
            cobj_metrics = conf[cobject]
            if not isinstance(cobj_metrics, dict):
                # ignoring fields, not metrics
                continue
            # parse object  instance=pretty|filters
            dsp_metrics = []
            rest, sep, na_object_filter = cobject.partition("|")
            na_object_name, sep, na_object_pretty = rest.partition('=')
            if sep:
                na_object_pretty = na_object_pretty.strip()
                dsp_metrics = match_var.findall(na_object_pretty)
                dsp_metrics += match_var_b.findall(na_object_pretty)
            if not sep:
                na_object_pretty = '@'
            NA_Object = NamedTuple('NA_Object', ['name', 'pretty', 'filter'])
            na_object = NA_Object(
                na_object_name,
                na_object_pretty,
                na_object_filter
            )
            # Get all metrics from the object
            try:
                info_metrics = server.get_info(na_object_name)
            except ValueError as e:
                msg = "'%s' metrics for '%s': %s"
                self.log.error(msg, na_object_name, device, str(e))
                continue
            obj_metrics = {}
            base_metrics = []
            for metric in cobj_metrics.keys():
                if isinstance(cobj_metrics[metric], dict):
                    msg = "Not allowed nested objects '%s' for '%s'"
                    self.log.error(msg, metric, device)
                    continue
                try:
                    (pretty, unit, prop, base, priv, publish) = \
                        self.__get_metric(
                            device,
                            metric,
                            info_metrics,
                            cobj_metrics[metric],
                            True
                        )
                except:
                    msg = "Not found metric '%s' for '%s'"
                    self.log.error(msg, metric, device)
                    continue
                if base:
                    base_metrics.append(base)
                obj_metrics[metric] = (pretty, unit, prop, base, priv, publish)
                counter_metrics += 1
            # Ref base metris
            for metric in base_metrics:
                if metric not in obj_metrics:
                    try:
                        obj_metrics[metric] = self.__get_metric(
                            device,
                            metric,
                            info_metrics,
                            metric,
                            False
                        )
                        counter_metrics += 1
                    except:
                        msg = "Not found metric '%s' for '%s'"
                        self.log.error(msg, metric, device)
            # Metrics from the name
            for metric in dsp_metrics:
                if metric not in obj_metrics:
                    try:
                        obj_metrics[metric] = self.__get_metric(
                            device,
                            metric,
                            info_metrics,
                            None,
                            False
                        )
                        counter_metrics += 1
                    except:
                        msg = "Not found metric '%s' for '%s'"
                        self.log.error(msg, metric, device)
            metrics[na_object] = obj_metrics
        self.metrics[device] = metrics
        self.log.info("%d metrics for '%s'", counter_metrics, device)
        return counter_metrics


    def process_config(self):
        """Process the configuration to enable/disable devices.

        Updates the internal structures of the collector.
        """
        if NaServer is None:
            self.log.error("Unable to import NetApp python API!")
            return
        super(OntapClusterCollector, self).process_config()
        if 'devices' in self.config:
            for device in self.config['devices']:
                if device not in self.dev_running:
                    self.last_collect_time[device] = {}
                    self.last_values[device] = {}
                    self.dev_running[device] = False
                try:
                    server = self._connect(device)
                    self.get_metrics(device, server)
                except Exception as e:
                    msg = "Cannot connect with '%s': %s"
                    self.log.error(msg, device, str(e))
                    continue
                try:
                    publish = int(self.config['devices'][device]['publish'])
                    if publish < 0 or publish > 2:
                        raise ValueError
                except:
                    self.log.error(
                        "Parameter 'publish' for %s must be [0, 1, 2]",
                        device
                    )
                interval = int(self.config['interval'])
                splay = int(self.config['splay'])
                self.log.info(
                    "Loading configuration for '%s': splay=%s, interval=%s",
                    device,
                    splay,
                    interval
                )
            deleted = []
            for device in self.dev_running:
                if device not in self.config['devices']:
                    deleted.append(device)
            for device in deleted:
                del self.dev_running[device]
                del self.last_collect_time[device]
                del self.last_values[device]
                del self.metrics[device]
                del self.connections[device]
                del self.reconnects[device]
                self.log.info("Deleted device: '%s'", device)
        else:
            self.log.error("[devices] not found in the configuration")
            self.config['devices'] = []


    def collect(self):
        """Collects the metrics.

        Diamond calls this funtion to collect the metrics. Starting on Diamond
        v4.0 due to the changes in the threading model, only sequencial device
        processingis possible. Now, the way to go is by creating different
        configuration files, one per NetApp device and Diamond will schedule
        each one in a different process.
        """
        interval = int(self.config['interval'])
        for device in self.config['devices']:
            if self.dev_running[device]:
                self.log.error(
                    "Cannot start metrics collection for '%s', another " \
                    "thread is running (http_timeout=%i)" %
                    (device, self.config['http_timeout'])
                )
                return
            self.dev_running[device] = True
            try:
                publish = int(self.config['devices'][device]['publish'])
                records = self.collect_device( device, interval, publish)
            except Exception as e:
                self.log.error(str(e))
            else:
                self.log.info(
                    "End collection for '%s' (%i metrics processed)",
                    device,
                    records
                )
            self.dev_running[device] = False


    def collect_device(self, device, interval, publish):
        """Collects the metrics for one filer/device.

        Returns the number of metrics processed.
        """
        max_interval = interval + interval * 0.5
        self.log.info("Starting metrics collection for '%s'" % device)
        total_records = 0
        server = self._connect(device)
        # We're only able to query a single object at a time,
        # so we'll loop over the objects.
        for na_object, metrics in self.metrics[device].iteritems():
            # na_object.name
            # na_object.pretty
            # na_object.filter
            try:
                instances = server.get_instances(
                    na_object.name, na_object.filter)
                if instances:
                    values, times, instance_t = server.get_metrics(
                        na_object.name, instances, metrics.keys())
                else:
                    self.log.error(
                        "No metrics '%s' with filter '%s' on %s",
                        na_object.name,
                        na_object.filter,
                        device
                    )
                    continue
            except IOError as e:
                self.log.error("Cannot connect to '%s': %s", device, str(e))
                continue
            # Process the records
            records_counter = 0
            for instance, data in values.iteritems():
                metrics_path = device
                for item in na_object.pretty.split('.'):
                    try:
                        item = item.replace('@', instance)
                        mtemplate = Template(item)
                        item = mtemplate.safe_substitute(data)
                        item = item.replace('.', '_').strip('_')
                        item = item.replace('/', '.').strip('.')
                        metrics_path += '.' + re.sub(
                            r'[^a-zA-Z0-9._]',
                            '_',
                            item
                        )
                    except Exception as e:
                        self.log.error(
                            "Cannot build metric name '%s' on '%s': %s",
                            na_object.pretty,
                            device,
                            str(e)
                        )
                # time delta
                try:
                    old_time = self.last_collect_time[device][metrics_path]
                except:
                    time_delta = 0
                else:
                    time_delta = instance_t - old_time
                    if time_delta <= 0:
                        self.log.warning(
                            "**time-delta <= 0s** for %s (from the API)!",
                            metrics_path
                        )
                        time_delta = times[instance] - old_time
                    if max_interval < time_delta:
                        self.log.warning(
                            "**too much time** between collects '%s': %s s",
                            metrics_path, time_delta
                        )
                self.last_collect_time[device][metrics_path] = instance_t
                #self.last_collect_time[device][metrics_path] = \
                #   times[instance]

                # process all metrics
                records_counter += self._publish_metrics(
                    device, instance, metrics_path,
                    data, time_delta, metrics, publish)
            # control the number of records
            if records_counter == 0:
                self.log.error(
                    "No instances for object '%s' on '%s'",
                    na_object,
                    device
                )
            total_records += records_counter


    def _publish_metrics(self, device, instance, metrics_path, data,
                         time_delta, metrics, publish):
        """Process and publish all metrics for an object.
        If a value is an array, it will process each value.

        Returns  number of processed metrics
        """
        counter = 0
        processed_values = {}
        for metric in metrics.keys():
            path = self.get_metric_path(metric, metrics_path)
            (pretty, unit, prop, base, priv, publish_metric) = metrics[metric]
            # if pretty is None, it will not be published
            if pretty is None:
                continue
            try:
                value = data[metric]
            except:
                self.log.error("Metric '%s' was not collected!", path)
                continue
            # Is it an array?
            value_list = []
            counter_key = 0
            for thing in value.split(','):
                try:
                    item = float(thing)
                except:
                    self.log.error("Metric '%s' not a number!", path)
                    break
                try:
                    key = pretty[counter_key]
                except:
                    key = metric + '_' + str(counter_key)
                value_list.append((key, item))
                counter_key += 1
            for name, value in value_list:
                pretty_path = self.get_metric_path(name, metrics_path)
                if prop == 1:   # raw
                    # As it was collected
                    result = self.raw_metric(pretty_path, value)
                elif prop == 2:  # rate
                    # metric - metric' / time
                    result = self.derivative_metric(
                        pretty_path,
                        value,
                        device,
                        True,
                        time_delta
                    )
                elif prop == 3:  # delta
                    # metric - metric'
                    result = self.derivative_metric(
                        pretty_path,
                        value,
                        device,
                        False
                    )
                elif prop == 4:  # average
                    # (metric - metric') / (ref_metric - ref_metric')
                    try:
                        result = self._calc_derivative_refmetric(
                            pretty_path,
                            value,
                            1.0,
                            base,
                            data,
                            metrics,
                            device,
                            metrics_path
                        )
                    except ValueError as e:
                        self.log.error(str(e))
                        continue
                elif prop == 5:   # percent
                    # 100 * (metric - metric') / (ref_metric - ref_metric')
                    try:
                        result = self._calc_derivative_refmetric(
                            pretty_path, value, 100.0, base, data,
                            metrics, device, metrics_path)
                    except ValueError as e:
                        self.log.error(str(e))
                        continue
                else:
                    publish_metric = False
                processed_values[pretty_path] = value
                counter += 1
                # Publish the metrics
                if publish_metric:
                    if result == 0.0 and publish == 2:
                        self.log.debug(
                            "Metric '%s' == 0.0 not published",
                            pretty_path
                        )
                    else:
                        self.publish_metric(Metric(
                            pretty_path, result, precision=4, host=device))
                else:
                    msg = "Metric '%s' not requested to be published"
                    self.log.debug(msg, pretty_path)
        # Move current values to last values
        self.last_values[device].update(processed_values)
        processed_values = {}
        return counter


    def raw_metric(self, name, new):
        """Raw metric calculator.

        Returns the value of the metric as it was collected.
        """
        return new


    def derivative_metric(self, name, value, device,
                          time_delta=True, interval=None, max_value=0):
        """Calculate the derivative of the metric.

        if it is a rate (time_delta=True)
        # metric - metric' / interval

        if it is a delta (time_delta=False)
        # metric - metric'

        where:
                metric = current value of metric
                metric' = previous value of metric
                interval = time delta between the two values
        """
        try:
            old = self.last_values[device][name]
            # Check for rollover
            if value < old:
                old = old - max_value
            # Get Change in X (value)
            derivative_x = value - old

            # Get Change in Y (time)
            derivative_y = 1.0
            if time_delta:
                # If we pass in a interval,
                # use it rather then the configured one
                if interval is None:
                    derivative_y = float(self.config['interval'])
                else:
                    derivative_y = interval
            result = derivative_x / derivative_y
        except Exception as e:
            msg = "Previous value for '%s' not found!. First time?"
            self.log.warning(msg, name)
            result = 0.0
        return result


    def _calc_derivative_refmetric(self, name, new, mult, ref_name,
                                   data, metrics, device, instance):
        """Prepare and calculate a derivate value of a metric depending on
        the values of another. It works with averages or percentages.
        """
        # mult * (metric - metric') / (ref_metric - ref_metric')
        try:
            ref_value = float(data[ref_name])
        except KeyError:
            path = self.get_metric_path(ref_name, instance)
            raise ValueError("Metric '%s' was not collected!" % path)
        except:
            path = self.get_metric_path(ref_name, instance)
            raise ValueError("Metric '%s' is not a float number!" % path)
        (pretty, unit, prop, base, priv, publish_metric) = metrics[ref_name]
        ref_path = self.get_metric_path(pretty[0], instance)
        return self.derivative_refmetric(
            name,
            new,
            ref_path,
            ref_value,
            device,
            mult
        )


    def derivative_refmetric(self, name, value, ref_name, ref_value, device,
                             pct=1.0, max_value=0.0):
        """Calculate a derivate value of a metric depending on the values
        of another.

        # pct * (metric - metric') / (ref_metric - ref_metric')

        where:
                metric = current value of metric
                metric' = previous value of metric
                ref_metric = current value of the base metric
                ref_metric' = previous value of the base metric
                pct = value of the multiplier. 100 to get a percentage
        """
        try:
            old = self.last_values[device][name]
            # Check for rollover
            if value < old:
                old = old - max_value
            # Get Change in X (value)
            derivative_x = value - old
        except:
            # Error
            msg = "Previous value for '%s' not found!. First time?"
            self.log.warning(msg, name)
            derivative_x = value
        try:
            # Not in last_processed_values, it must be raw!!!!
            old = self.last_values[device][ref_name]
            # Check for rollover
            if ref_value < old:
                old = old - max_value
            # Get Change in X (value)
            derivative_y = ref_value - old
        except:
            msg = "Previous value for '%s' not found!. First time?"
            self.log.warning(msg, ref_name)
            derivative_y = ref_value
        # calc
        try:
            result = pct * derivative_x / derivative_y
        except:
            # Division by 0
            self.log.debug(
                "Division by zero: %s=%s/%s=%s",
                name,
                derivative_x,
                ref_name,
                derivative_y
            )
            result = 0.0
        return result


    def get_metric_path(self, name, instance=None):
        """Gets metric path.

        Returns the metric path.
        """
        value_list = []
        value = ''
        try:
            value = self.config['path_prefix']
            if value:
                value_list.append(value)
        except:
            pass
        if instance is not None:
            value_list.append(instance)
        try:
            value = self.config['path_suffix']
            if value:
                value_list.append(value)
        except:
            pass
        value_list.append(name)
        return '.'.join(value_list)


# End of Diamond Collector Plugin

class NetAppMetrics:

    perf_max_records = 500

    def __init__(self, device, user, password, 
                 apiversion='1.12', timeout=None, vserver=''):
        self.vserver = None
        self.device = None
        self.clustered = False
        self.generation = '0'
        self.major = '0'
        self.minor = '0'
        self.apimajor = 0
        self.apiminor = 0
        self._connect(device, user, password, apiversion, timeout)
        self._set_vserver(vserver)
        self._get_version()

    def _connect(self, device, user, password, apiversion, 
                 timeout=None, method='HTTP'):
        try:
            self.apimajor = int(apiversion.split('.')[0])        
            self.apiminor = int(apiversion.split('.')[1])
        except:
            raise ValueError("incorrect API version: '%s'" % apiversion)
        self.server = NaServer.NaServer(device, self.apimajor, self.apiminor)
        self.server.set_transport_type(method)
        self.server.set_style('LOGIN')
        self.server.set_admin_user(user, password)
        if timeout is not None:
            self.server.set_timeout(timeout)
        self.device = device

    def _set_vserver(self, vserver=''):
        self.server.set_vserver(vserver)
        self.vserver = vserver

    def _get_version(self):
        cmd = NaServer.NaElement('system-get-version')
        res = self.server.invoke_elem(cmd)
        if res.results_errno():
            raise ValueError(
                "system-get-version error: %s" % res.results_reason())
        else:
            self.clustered = False
            clustered = res.child_get_string("is-clustered")
            if clustered == "true":
                self.clustered = True
            version_tuple = res.child_get("version-tuple")
            if version_tuple:
                version_tuple = version_tuple.child_get("system-version-tuple")
                self.generation = version_tuple.child_get_string("generation")
                self.major = version_tuple.child_get_string("major")
                self.minor = version_tuple.child_get_string("minor")
            else:
                version = res.child_get_string("version")
                if version:
                    version_tuple = re.search(r'(\d+)\.(\d+)\.(\d+)', version)
                    self.generation = version_tuple.group(1)
                    self.major = version_tuple.group(2)
                    self.minor = version_tuple.group(3)
            return (self.generation, self.major, self.minor)

    def get_objects(self):
        cmd = NaServer.NaElement('perf-object-list-info')
        res = self.server.invoke_elem(cmd)
        objects = {}
        if res.results_errno():
            raise ValueError(
                "perf-object-list-info error: %s" % res.results_reason())
        else:
            for inst in res.child_get("objects").children_get():
                inst_name = inst.child_get_string("name")
                inst_desc = inst.child_get_string("description")
                inst_priv = inst.child_get_string("privilege-level")
                objects[inst_name] = (inst_desc, inst_priv)
        return objects

    def get_info(self, kind):
        cmd = NaServer.NaElement("perf-object-counter-list-info")
        cmd.child_add_string("objectname", kind)
        res = self.server.invoke_elem(cmd)
        counters = {}
        if res.results_errno():
            reason = res.results_reason()
            msg = "perf-object-counter-list-info cannot collect '%s': %s"
            raise ValueError(msg % (kind, reason))
        for counter in res.child_get("counters").children_get():
            name = counter.child_get_string("name")
            desc = counter.child_get_string("desc")
            unit = ''
            if counter.child_get_string("unit"):
                unit = counter.child_get_string("unit")
            properties = ''
            if counter.child_get_string("properties"):
                properties = counter.child_get_string("properties")
            base = ''
            if counter.child_get_string("base-counter"):
                base = counter.child_get_string("base-counter")
            priv = counter.child_get_string("privilege-level")
            labels = []
            if counter.child_get("labels"):
                clabels = counter.child_get("labels")
                if clabels.child_get_string("label-info"):
                    tlabels = clabels.child_get_string("label-info")
                    labels = [l.strip() for l in tlabels.split(',')]
            counters[name] = (unit, properties, base, priv, desc, labels)
        return counters

    def _invoke(self, cmd):
        '''Exposes underlying NetApp API for invoking'''
        return self.server.invoke(cmd)

    def _invoke_elem(self, cmd):
        '''Exposes underlying NetApp API for element invoking'''
        if isinstance(cmd, NaServer.NaElement):
            return self.server.invoke_elem(cmd)
        raise TypeError('Provided cmd is not of type NaElement')

    def _decode_elements2dict(self, head, listfilter=None, output={}):
        '''Takes the results from an invoke call from the NetApp
        API and break it down to a Python dict object.'''
        if listfilter is not None:
            if not (hasattr(listfilter, "__iter__") or
                hasattr(filter, "__getitem__")):
                raise TypeError('listfilter is no a iterable!')
        if head.has_children() == 1:
            aux = {}
            for child in head.children_get():
                if child.has_children() == 1:
                    aux = self._decode_elements2dict(child, listfilter, aux)
                else:
                    if listfilter is not None and \
                        child.element['name'] not in listfilter:
                        continue;
                    aux[child.element['name']] = child.element['content']
            output[head.element['name']] = aux
        else:
            if listfilter is not None:
                if child.element['name'] in listfilter:
                    output[head.element['name']] = head.element['content']
            else:
                output[head.element['name']] = head.element['content']
        return output

    def __sevenm_instances(self, kind, filter=''):
        instances_list = []
        cmd = NaServer.NaElement("perf-object-instance-list-info-iter-start")
        cmd.child_add_string("objectname", kind)
        res = self.server.invoke_elem(cmd)
        if res.results_errno():
            reason = res.results_reason()
            msg = (
                    "perf-object-instance-list-info-iter-start"
                    " cannot collect '%s': %s"
                  )
            raise ValueError(msg % (kind, reason))
        next_tag = res.child_get_string("tag")
        counter = self.perf_max_records
        while counter == self.perf_max_records:
            cmd = NaServer.NaElement(
                "perf-object-instance-list-info-iter-next"
            )
            cmd.child_add_string("tag", next_tag)
            cmd.child_add_string("maximum", self.perf_max_records)
            res = self.server.invoke_elem(cmd)
            if res.results_errno():
                reason = res.results_reason()
                msg = ("perf-object-instance-list-info-iter-next"
                       " cannot collect '%s': %s")
                raise ValueError(msg % (kind, reason))
            counter = res.child_get_string("records")
            instances = res.child_get("instances")
            if instances:
                for inst in instances.children_get():
                    name = inst.child_get_string("name")
                    instances_list.append(name)
        cmd = NaServer.NaElement("perf-object-instance-list-info-iter-end")
        cmd.child_add_string("tag", next_tag)
        res = self.server.invoke_elem(cmd)
        if res.results_errno():
            reason = res.results_reason()
            msg = (
                    "perf-object-instance-list-info-iter-end"
                    " cannot collect '%s': %s"
            )
            raise ValueError(msg % (kind, reason))

        # filter
        return instances_list

    def __clusterm_instances(self, kind, filter=''):
        counter = self.perf_max_records
        next_tag = ''
        instances_list = []
        while counter == self.perf_max_records:
            cmd = NaServer.NaElement("perf-object-instance-list-info-iter")
            cmd.child_add_string("objectname", kind)
            if filter:
                cmd.child_add_string("filter-data", filter)
            if next_tag:
                cmd.child_add_string("tag", next_tag)
            cmd.child_add_string("max-records", self.perf_max_records)
            res = self.server.invoke_elem(cmd)
            if res.results_errno():
                reason = res.results_reason()
                msg = (
                    "perf-object-instance-list-info-iter"
                    " cannot collect '%s': %s"
                )
                raise ValueError(msg % (kind, reason))
            next_tag = res.child_get_string("next-tag")
            counter = res.child_get_string("num-records")
            attr_list = res.child_get("attributes-list")
            if attr_list:
                for inst in attr_list.children_get():
                    name = inst.child_get_string("uuid")
                    instances_list.append(name)
        return instances_list

    def get_instances(self, kind, filter=''):
        if self.clustered:
            return self.__clusterm_instances(kind, filter)
        else:
            return self.__sevenm_instances(kind, filter)

    def __collect_instances(self, response):
        metrics = {}
        times = {}
        for instance in response.child_get("instances").children_get():
            instance_data = {}
            counters_list = instance.child_get("counters").children_get()
            for counter in counters_list:
                raw_metricname = counter.child_get_string("name")
                raw_metricname = unicodedata.normalize('NFKD', raw_metricname)
                metric = raw_metricname.encode('ascii', 'ignore')
                instance_data[metric] = counter.child_get_string("value")
            # get a instance name
            if instance.child_get_string("uuid"):
                name = instance.child_get_string("uuid")
            else:
                name = instance.child_get_string("name")
            name = unicodedata.normalize('NFKD', name)
            # Optimize please!!!!!
            name = name.encode('ascii', 'ignore')
            name = name.replace('.', '_').strip('_')
            name = name.replace('/', '.').strip('.')
            name = re.sub(r'[^a-zA-Z0-9._]', '_', name)
            #name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
            metrics[name] = instance_data
            # Keep track of how long has passed since we checked last
            times[name] = time.time()
        instance_time = None
        if response.child_get_string("timestamp"):
            instance_time = float(response.child_get_string("timestamp"))
        return metrics, times, instance_time

    def __sevenm_metrics(self, kind, instances, metrics):
        values = {}
        times = {}
        cmd = NaServer.NaElement("perf-object-get-instances-iter-start")
        cmd.child_add_string("objectname", kind)
        counters = NaServer.NaElement("counters")
        for metric in metrics:
            counters.child_add_string("counter", metric)
        cmd.child_add(counters)
        insts = NaServer.NaElement("instances")
        for inst in instances:
            insts.child_add_string("instance", inst)
        cmd.child_add(insts)
        res = self.server.invoke_elem(cmd)
        if res.results_errno():
            reason = res.results_reason()
            msg = (
                    "perf-object-get-instances-iter-start"
                    " cannot collect '%s': %s"
            )
            raise ValueError(msg % (kind, reason))
        next_tag = res.child_get_string("tag")
        instance_time = float(res.child_get_string("timestamp"))
        counter = self.perf_max_records
        while counter == self.perf_max_records:
            cmd = NaServer.NaElement("perf-object-get-instances-iter-next")
            cmd.child_add_string("tag", next_tag)
            cmd.child_add_string("maximum", self.perf_max_records)
            res = self.server.invoke_elem(cmd)
            if res.results_errno():
                reason = res.results_reason()
                msg = (
                        "perf-object-get-instances-iter-next"
                        " cannot collect '%s': %s"
                )
                raise ValueError(msg % (kind, reason))
            counter = res.child_get_string("records")
            partial_values, partial_times, partial_inst_t \
                = self.__collect_instances(res)
            # Mix them with the previous records of the same instance
            # WARNING, BUG with same instance and time!!!!!!!!!
            for instance, values in values.iteritems():
                if instance in partial_values:
                    values.update(partial_values[instance])
                    del partial_values[instance]
            values.update(partial_values)
            times.update(partial_times)
        cmd = NaServer.NaElement("perf-object-instance-list-info-iter-end")
        cmd.child_add_string("tag", next_tag)
        res = self.server.invoke_elem(cmd)
        if res.results_errno():
            reason = res.results_reason()
            msg = (
                    "perf-object-instance-list-info-iter-end"
                    " cannot collect '%s': %s"
            )
            raise ValueError(msg % (kind, reason))
        return values, times, instance_time

    def __clusterm_metrics(self, kind, instances, metrics):
        cmd = NaServer.NaElement("perf-object-get-instances")
        inst = NaServer.NaElement("instance-uuids")
        for instance in instances:
            inst.child_add_string("instance-uuid", instance)
        cmd.child_add(inst)
        cmd.child_add_string("objectname", kind)
        counters = NaServer.NaElement("counters")
        for metric in metrics:
            counters.child_add_string("counter", metric)
        cmd.child_add(counters)
        res = self.server.invoke_elem(cmd)
        if res.results_errno():
            reason = res.results_reason()
            msg = "perf-object-get-instances cannot collect '%s': %s"
            raise ValueError(msg % (kind, reason))
        return self.__collect_instances(res)

    def get_metrics(self, kind, instances, metrics=[]):
        if self.clustered:
            return self.__clusterm_metrics(kind, instances, metrics)
        else:
            return self.__sevenm_metrics(kind, instances, metrics)


# TODO: Change to argparse
# command line

def usage(program):
    print """Standalone program and/or Diamond plugin to retrive metrics
and info from NetApp devices. It supports 7-Mode anc C-Mode.
Usage:

    {0} [-h | --help]
    {0} [-v <api.version>] -s <server> -u <user> -p <password> [action]

Where <action> could be:

 * objects : returns all objects available on the device
 * info <object> : returns all metrics for <object>
 * instances <object> : returns the name of all instaces of <object>
 * metrics <object> [instace]: returns all counters for all instances
   or if one instances is provided, only for that one.

(c) Jose Riguera Lopez, 2013-2015 <jose.riguera@springer.com>

    """.format(program)


def main(argv):
    sort_ops = "hv:s:u:p:f:"
    long_ops = ["help", "api=", "server=", "user=", "password=", "filter="]
    try:
        opts, args = getopt.getopt(argv[1:], sort_ops, long_ops)
    except getopt.GetoptError as err:
        print str(err)
        usage(argv[0])
        sys.exit(2)
    server = ''
    user = ''
    password = ''
    filter = ''
    apiversion = '1.12'
    for o, a in opts:
        if o in ("-h", "--help"):
            usage(argv[0])
            sys.exit()
        elif o in ("-v", "--api"):
            apiversion = a
        elif o in ("-s", "--server"):
            server = a
        elif o in ("-u", "--user"):
            user = a
        elif o in ("-p", "--password"):
            password = a
        elif o in ("-p", "--filter"):
            filter = a
    if not server or not user:
        usage(argv[0])
        sys.exit(2)
    netapp = NetAppMetrics(server, user, password, apiversion)
    print(
            "Server=%s, version=%s.%s.%s, date=%s" % (
                server,
                netapp.generation,
                netapp.major,
                netapp.minor,
                datetime.datetime.now()
            )
    )
    if not args:
        sys.exit(0)
    elif args[0] == 'objects':
        print("Available objects:")
        objects = netapp.get_objects()
        for k, v in sorted(objects.iteritems()):
            print("\t %s" % k)
            print("\t\t Description: %s" % v[0])
        print("\n %d objects found" % len(objects))
    elif args[0] == 'info':
        try:
            item = args[1]
        except:
            print("You need to specify the object!")
            sys.exit(1)
        print("Counters for %s:" % item)
        try:
            info = netapp.get_info(item)
            for k, v in sorted(info.iteritems()):
                (unit, properties, base, priv, desc, labels) = v
                print(
                    "%s => unit=%s, priv_level=%s, array_labels=%s" % (
                        k,
                        unit,
                        priv,
                        labels
                    )
                )
                print("\t properties=%s, base=%s" % (properties, base))
                print("\t %s \n" % desc)
            print("%d metrics found" % len(info))
        except Exception as e:
            print(str(e))
            sys.exit(1)
    elif args[0] == 'instances':
        try:
            item = args[1]
        except:
            print("You need to specify the object!")
            sys.exit(1)
        try:
            filter = args[2]
        except:
            filter = ''
        print("Instances of %s (filter='%s'):" % (item, filter))
        try:
            instances = netapp.get_instances(item, filter)
            for i in sorted(instances):
                print("\t %s" % i)
            print("%d instances found" % len(instances))
        except Exception as e:
            print(str(e))
            sys.exit(1)
    elif args[0] == 'metrics':
        try:
            item = args[1]
        except:
            print("You need to specify the object!")
            sys.exit(1)
        try:
            inst = [args[2]]
        except:
            try:
                inst = netapp.get_instances(item)
            except Exception as e:
                print(str(e))
                sys.exit(1)
        try:
            m, t, inst_t = netapp.get_metrics(item, inst)
        except Exception as e:
            print(str(e))
            sys.exit(1)
        for k, v in sorted(m.iteritems()):
            print("%s (%s):" % (k,  datetime.datetime.fromtimestamp(inst_t)))
            for k2, v2 in sorted(v.iteritems()):
                print("\t %s = %s" % (k2, v2))
            print
        print("%d instances found" % len(m))
    else:
        print("What do you want?")


if __name__ == "__main__":
    main(sys.argv)

# EOF
