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
import glob

import yaml
from ClusterShell.NodeSet import NodeSet

from hpci2sync.cluster import ClustersSet, Equipment
from hpci2sync.hieradata import Hieradata

class PrivateData(object):

    def __init__(self, conf, networks):

        self.conf = conf
        self.clusters = ClustersSet()
        self.hieradata = Hieradata(conf, self.clusters, networks)

    def parse(self):
        # first parse equipments specs then master_network in hieradata
        self.parse_equipments()
        self.hieradata.parse()
        return self.clusters

    def parse_equipments(self):

        clusters = os.listdir(self.conf.dir_equipments)
        logger.debug("discovered clusters: %s", str(clusters))
        for cluster in clusters:
            if cluster in self.conf.exclude_clusters:
                logger.debug("skipping cluster %s because excluded",
                             cluster)
                continue  # jump to next cluster iteration
            self.parse_cluster(cluster)

    def parse_cluster(self, name):

        logger.debug("parsing cluster %s", name)

        cluster = self.clusters.add(name)

        glob_eqt_files = os.path.join(self.conf.dir_equipments, name, '*.yaml')
        equipment_files = glob.glob(glob_eqt_files)
        for equipment_file in equipment_files:
            if os.path.basename(equipment_file) == 'misc.yaml':
                self.parse_misc_file(cluster, equipment_file)
            else: 
                self.parse_equipment_file(cluster, equipment_file)

    def parse_equipment_file(self, cluster, equipment_file):

        category = os.path.splitext(os.path.basename(equipment_file))[0]
        logger.debug("parsing equipment_file %s (category: %s)",
                     equipment_file, category)

        with open(equipment_file, 'r') as stream:
            try:
                data = yaml.load(stream)
                for hostlist, params in data.iteritems():
                    self.parse_equipment_set(cluster, category,
                                             hostlist, params)

            except yaml.YAMLError as exc:
                logger.error("error while parsing yaml file %s: %s",
                             equipment_file, exc)

    def parse_misc_file(self, cluster, file_path):

        logger.debug("parsing misc equipment file %s", file_path)

        with open(file_path, 'r') as stream:
            try:
                data = yaml.load(stream)
                for hostlist, params in data.iteritems():
                    category = params['category']
                    self.parse_equipment_set(cluster, category,
                                             hostlist, params)

            except yaml.YAMLError as exc:
                logger.error("error while parsing yaml file %s: %s",
                             equipment_file, exc)

    def parse_equipment_set(self, cluster, category, hostlist, params):

        logger.debug("parsing equipment set %s", hostlist)
        nodeset = NodeSet(hostlist)
        for host in nodeset:
            equipment = Equipment(host)
            equipment.category = category
            if equipment.category == 'server':
                try:
                    equipment.extract_role(cluster.prefix)
                except RuntimeError:
                    logger.error("unable to extract role from equipement "
                                 "name %s", equipment.name)
                    continue  # skip server, continue with next equipment
            equipment.model = params.get('model')
            cluster.equipments.add(equipment)
