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

import re

class ClustersSet(object):

    def __init__(self):

        self._clusters = set()

    def __contains__(self, cluster_name):

        return Cluster(cluster_name) in self._clusters

    def __iter__(self):

        for cluster in self._clusters:
            yield cluster

    def add(self, name):

        new_cluster = Cluster(name)
        self._clusters.add(new_cluster)
        return new_cluster

    def get(self, name): 
        for cluster in self._clusters:
            if cluster.name == name:
                return cluster
        raise KeyError("cluster %s not found" % (name))


class Cluster(object):

    def __init__(self, name):

        self.name = name
        self.equipments = set()

    def __eq__(self, other):

        return self.name == other.name

    def __hash__(self):

        return hash(self.name)

    def __contains__(self, name):

        return Equipment(name) in self.equipments

    def __iter__(self):

        for equipment in sorted(self.equipments, key=lambda equipment: equipment.name):
            yield equipment

    @property
    def prefix(self):
        return self.name[:2]

    def get_equipment(self, name):
        for equipment in self.equipments:
            if equipment.name == name:
                return equipment
        raise KeyError("equipment %s not found in cluster %s"
                       % (name, self.name))
 
class Netif(object):

    def __init__(self, network, ip):

        self.network = network
        self.ip = ip


class Equipment(object):

    def __init__(self, name):

        self.name = name
        self.fqdn = None
        self.category = None
        self.model = None
        self.netifs = set()
        # the following attributes are only set for server category
        self.role = None
        self.profiles = None

        # the IP address that should finally appear in conf
        self.ip = None
        # the attributes of the host in conf
        self.attrs = {}

    def __eq__(self, other):

        return self.name == other.name

    def __hash__(self):

        return hash(self.name)

    def extract_role(self, prefix):

        match = re.match(r"%s([a-z]+[a-z0-9]*[a-z]+)[0-9]*" % (prefix), self.name)
        if not match:
            raise RuntimeError
        self.role = match.group(1)
        logger.debug("role of %s is %s", self.name, self.role)

    def add_netif(self, network, ip):

        self.netifs.add(Netif(network, ip))

    def get_ip_netif(self, role):

        for netif in self.netifs:
            if netif.network.role == role:
                return netif.ip
        return None

    def set_attrs(self):

        # add BMC and profiles for servers
        if self.category == 'server':

            bmc_ip = self.get_ip_netif('bmc')
            if bmc_ip is not None:
                self.attrs['bmc'] = bmc_ip

            if self.profiles is not None:
                self.attrs['profiles'] = self.profiles

        self.attrs['category'] = self.category
        if self.model is not None:
            self.attrs['model'] = self.model

    @property
    def wan_connected_only(self):
        if len(self.netifs) == 0:
            logger.warning("equipment %s is not connected to any network",
                           self.name)
            return False

        for netif in self.netifs:
            if netif.network.role != 'wan':
                return False
        return True

    def has_profile(self, profiles):
        if self.profiles is None:
            return False 
        return len(set(self.profiles).intersection(profiles)) > 0

    def monitored_by_master(self, profiles):
        return self.wan_connected_only or \
               self.has_profile(profiles)

    def monitored_by_satellite(self, profiles):
        return not self.monitored_by_master(profiles)


class NetworksSet(object):

    def __init__(self):

        self._networks = set()

    def __contains__(self, network_name):

        return Network('fakeforin', name) in self._networks

    def add(self, role, name):

        self._networks.add(Network(role, name))

    def get(self, name): 
        for network in self._networks:
            if network.name == name:
                return network
        raise KeyError("network %s not found" % (name))


class Network(object):

    def __init__(self, role, name):

        self.role = role
        self.name = name
