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

import ConfigParser
from io import StringIO

class ConfRun(object):
    """Runtime configuration class."""

    def __init__(self):

        self.debug = False
        self.dryrun = False
        self.conf_file = None
        self.action = None

        self.dir_icinga2 = None
        self.dir_ca = None
        self.dir_crtdst = None
        self.dir_privatadata = None
        self.dir_hieradata = None
        self.dir_equipments = None
        self.dir_conf = None
        self.dir_tmp = None
        self.file_hosts = None
        self.file_keys = None

        self.net_adm = None
        self.net_wan = None
        self.net_mgt = None
        self.net_bmc = None
        self.net_exclude = []

        # certs params
        self.exclude_clusters = []
        self.nodes_roles = []

        # conf params
        self.profs_master = []
        self.prof_monsat = None
        self.dir_templates = None
        self.conf_owner = None

    def dump(self):

        logger.debug("runtime configuration dump:")
        logger.debug("- debug: %s", str(self.debug))
        logger.debug("- dryrun: %s", str(self.dryrun))
        logger.debug("- conf_file: %s", str(self.conf_file))
        logger.debug("- action: %s", str(self.action))
        logger.debug("- dir_icinga2: %s", str(self.dir_icinga2))
        logger.debug("- dir_ca: %s", str(self.dir_ca))
        logger.debug("- dir_crtdst: %s", str(self.dir_crtdst))
        logger.debug("- dir_privatedata: %s", str(self.dir_privatedata))
        logger.debug("- dir_hieradata: %s", str(self.dir_hieradata))
        logger.debug("- dir_equipments: %s", str(self.dir_equipments))
        logger.debug("- dir_conf: %s", str(self.dir_conf))
        logger.debug("- dir_tmp: %s", str(self.dir_tmp))
        logger.debug("- net_adm: %s", str(self.net_adm))
        logger.debug("- net_wan: %s", str(self.net_wan))
        logger.debug("- net_mgt: %s", str(self.net_mgt))
        logger.debug("- file_hosts: %s", str(self.file_hosts))
        logger.debug("- file_keys: %s", str(self.file_keys))
        logger.debug("- exclude_clusters: %s", str(self.exclude_clusters))
        logger.debug("- nodes_roles: %s", str(self.nodes_roles))
        logger.debug("- profs_master: %s", str(self.profs_master))
        logger.debug("- prof_monsat: %s", str(self.prof_monsat))
        logger.debug("- dir_templates: %s", str(self.dir_templates))
        logger.debug("- conf_owner: %s", str(self.conf_owner))

    def parse(self):

        """Parse configuration file and set runtime configuration accordingly.
           Here are defined default configuration file parameters."""
        defaults = StringIO(
          u"[paths]\n"
          "icinga2 = /etc/icinga2\n"
          "privatedata = /root/hpc-privatedata\n"
          "ca = /var/lib/icinga2/ca\n"
          "crtdst = %(privatedata)s/files/${cluster}/icinga2/certs\n"
          "hieradata = %(privatedata)s/hieradata\n"
          "equipments = %(privatedata)s/monitoring/equipments\n"
          "conf = %(privatedata)s/monitoring/conf\n"
          "tmp = /tmp/hpci2sync\n"
          "hosts = network.yaml\n"
          "keys = /etc/hpci2sync/keys.ini\n"
          "[networks]\n"
          "administration = administration\n"
          "wan = wan\n"
          "management = management\n"
          "bmc = bmc\n"
          "exclude = lowlatency\n"
          "[certs]\n"
          "exclude_clusters = gen\n"
          "nodes_roles = cn,gn,bm\n"
          "[conf]\n"
          "profiles_master = virt::host\n"
          "profile_monsat = monitoring::server\n"
          "templates = /etc/hpci2sync/templates\n"
          "owner = nagios\n")
        parser = ConfigParser.SafeConfigParser()
        parser.readfp(defaults)
        parser.read(self.conf_file)
        self.dir_icinga2 = parser.get('paths', 'icinga2')
        self.dir_ca = parser.get('paths', 'ca')
        self.dir_crtdst = parser.get('paths', 'crtdst')
        self.dir_privatedata = parser.get('paths', 'privatedata')
        self.dir_hieradata = parser.get('paths', 'hieradata')
        self.dir_equipments = parser.get('paths', 'equipments')
        self.dir_conf = parser.get('paths', 'conf')
        self.dir_tmp = parser.get('paths', 'tmp')
        self.net_adm = parser.get('networks', 'administration')
        self.net_wan = parser.get('networks', 'wan')
        self.net_mgt = parser.get('networks', 'management')
        self.net_bmc = parser.get('networks', 'bmc')
        self.net_exclude = parser.get('networks', 'exclude').split(',')
        self.file_hosts = parser.get('paths', 'hosts')
        self.file_keys = parser.get('paths', 'keys')
        self.exclude_clusters = parser.get('certs', 'exclude_clusters').split(',')
        self.nodes_roles = parser.get('certs', 'nodes_roles').split(',')
        self.profs_master = parser.get('conf', 'profiles_master').split(',')
        self.prof_monsat = parser.get('conf', 'profile_monsat')
        self.profs_master.append(self.prof_monsat)
        self.dir_templates = parser.get('conf', 'templates')
        self.conf_owner = parser.get('conf', 'owner')

    def override(self, args):
        """Override configuration files parameters with args values."""
        pass
