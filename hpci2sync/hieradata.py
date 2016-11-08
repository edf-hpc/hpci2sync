#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2016 EDF SA
#
#  This file is part of hpci2sync
#
#  This software is governed by the CeCILL license under French law and
#  abiding by the rules of distribution of free software. You can use,
#  modify and/ or redistribute the software under the terms of the CeCILL
#  license as circulated by CEA, CNRS and INRIA at the following URL
#  "http://www.cecill.info".
#
#  As a counterpart to the access to the source code and rights to copy,
#  modify and redistribute granted by the license, users are provided only
#  with a limited warranty and the software's author, the holder of the
#  economic rights, and the successive licensors have only limited
#  liability.
#
#  In this respect, the user's attention is drawn to the risks associated
#  with loading, using, modifying and/or developing or reproducing the
#  software by the user in light of its specific status of free software,
#  that may mean that it is complicated to manipulate, and that also
#  therefore means that it is reserved for developers and experienced
#  professionals having in-depth computer knowledge. Users are therefore
#  encouraged to load and test the software's suitability as regards their
#  requirements in conditions enabling the security of their systems and/or
#  data to be ensured and, more generally, to use and operate it in the
#  same conditions as regards security.
#
#  The fact that you are presently reading this means that you have had
#  knowledge of the CeCILL license and that you accept its terms.

import logging
logger = logging.getLogger(__name__)

import os
import yaml

class Hieradata(object):

    def __init__(self, conf, clusters, networks):

        self.conf = conf
        self.path = self.conf.dir_hieradata
        self.clusters = clusters
        self.networks = networks

    def parse(self):

        logger.info("parsing hieradata")
        cluster_dirs = [ found_dir for found_dir in os.listdir(self.path)
                         if os.path.isdir(os.path.join(self.path, found_dir)) ]
        logger.debug("discovered clusters: %s", str(cluster_dirs))
        for cluster in cluster_dirs:
            if cluster in self.conf.exclude_clusters:
                logger.debug("skipping cluster %s because excluded",
                             cluster)
                continue  # jump to next cluster iteration

            if cluster not in self.clusters:
                logger.warning("cluster %s not found in initialized cluster "
                               "set", cluster)
                continue  # jump to next cluster iteration

            self.parse_cluster(cluster)

    def parse_cluster(self, name):

        logger.debug("parsing hieradata for cluster %s", name)
        cluster = self.clusters.get(name)

        host_file = os.path.join(self.path, name, self.conf.file_hosts)
        with open(host_file, 'r') as stream:
            try:
                data = yaml.load(stream)
                hosts = data['master_network']
                logger.debug("hosts: type(%s), len(%d)", type(hosts), len(hosts))

                for host, params in hosts.iteritems():
                    self.parse_host(cluster, host, params)

            except yaml.YAMLError as exc:
                logger.error("error while parsing host file %s: %s",
                             host_file, exc)

    def parse_host(self, cluster, host, params):

        if host not in cluster:
            logger.warning("host %s not found in initialized cluster %s",
                           host, cluster.name)
            return

        equipment = cluster.get_equipment(host)

        equipment.fqdn = params['fqdn']

        self.parse_host_netifs(equipment, params['networks'])
        self.parse_host_profiles(cluster, equipment)

    def parse_host_netifs(self, equipment, netifs):

        if not len(netifs):
            logger.warning("host %s is not connected to any network",
                           equipment.name)
            return

        for net_name, net_settings in netifs.iteritems():

            # special handling for BMC
            if net_name == self.conf.net_bmc \
               and equipment.category != 'server':
                logger.error("equipment %s in category %s cannot have a BMC",
                             equipment.name, equipment.category)
                continue

            if net_name in self.conf.net_exclude:
                logger.debug("skipping %s netif on network %s because "
                             "excluded",
                             equipment.name, net_name)
                continue
            
            equipment.add_netif(self.networks.get(net_name),
                                net_settings['IP'])

    def parse_host_profiles(self, cluster, equipment):

        if equipment.category != 'server':
            logger.debug("skipping profiles parsing for not server equipment "
                         "%s", equipment.name)
            return
        
        role_file = os.path.join(self.path, cluster.name, 'roles',
                                 equipment.role + '.yaml')

        if not os.path.exists(role_file):
            logger.warning("cannot parse %s profiles because role file %s "
                           "does not exist",
                           equipment.name, role_file)
            return

        prefix = 'profiles::' 

        with open(role_file, 'r') as stream:
            try:
                data = yaml.load(stream)
                equipment.profiles = [ profile[len(prefix):]
                                       for profile in data['profiles']]
                logger.debug("equipment %s profiles: %s",
                             equipment.name,
                             str(equipment.profiles))

            except yaml.YAMLError as exc:
                logger.error("error while parsing role file %s: %s",
                             role_file, exc)
