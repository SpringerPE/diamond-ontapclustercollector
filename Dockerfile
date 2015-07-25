# diamond-ontapclustercollector
#
# VERSION  0.2.0
#
# Use phusion/baseimage as base image.
# https://github.com/phusion/baseimage-docker/blob/master/Changelog.md
#
FROM phusion/baseimage:0.9.17
MAINTAINER Jose Riguera <jriguera@gmail.com>

# Set correct environment variables.
ENV HOME /root
ENV DEBIAN_FRONTEND noninteractive

# Delete ssh_gen_keys
RUN rm -rf /etc/service/sshd /etc/my_init.d/00_regen_ssh_host_keys.sh

# Update
RUN apt-get update && apt-get upgrade -y -o Dpkg::Options::="--force-confold"
 
# Install Python and Basic Python Tools
RUN apt-get install -y python-minimal python-pip python-configobj python-psutil python-setuptools 

# Install Diamond from the base folder
#ENV USE_SETUPTOOLS 1
#ADD diamond /tmp/
#RUN cd /tmp/diamond/ && python setup.py install
# or from PIP
RUN pip install diamond 

# Install OntapClusterCollector
ADD src/ /usr/local/share/diamond/collectors/
ADD conf/OntapClusterCollector.conf* conf/OntapClusterCollector*.template /etc/diamond/collectors/
ADD conf/diamond-ontap-configurator.sh /usr/local/bin/

# prepare to run
ADD docker/bin/ /usr/bin/
ADD docker/confd/ /etc/confd/
ADD docker/init/ /etc/my_init.d/

# runinit
RUN mkdir /etc/service/confd && mkdir /etc/service/diamond
ADD docker/confd.sh /etc/service/confd/run
ADD docker/diamond.sh /etc/service/diamond/run

# Use baseimage-docker's init system.
CMD ["/sbin/my_init"]

# Clean up APT when done.
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
