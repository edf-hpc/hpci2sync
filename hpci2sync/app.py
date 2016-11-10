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
import sys
import subprocess
import shutil
from string import Template
import difflib
import pwd

import jinja2

from hpci2sync.args import parse_args
from hpci2sync.conf import ConfRun
from hpci2sync.keys import KeysManager
from hpci2sync.cluster import NetworksSet
from hpci2sync.privatedata import PrivateData
from hpci2sync.tmp import TmpDirManager

class MainApp(object):

    def __init__(self):

        self.conf = ConfRun()
        self.args = parse_args(self.conf)
        self.setup_logger()  # setup logger early for conf parsing

        self.conf.parse()
        self.conf.override(self.args)

        self.conf.dump()
        self.keys = KeysManager(self.conf.file_keys)

        self.clusters = None
        self.networks = None

        # used for certs
        self.all_certs_ok = True

        # used for conf
        self.tmpdir = None

    def setup_logger(self):

        app_logger = logging.getLogger('hpci2sync')
        if self.conf.debug is True:
            app_logger.setLevel(logging.DEBUG)
        else:
            app_logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        handler.setFormatter(formatter)
        app_logger.addHandler(handler)

    def run(self):

        if self.conf.action == 'certs':
            self._sync_certs()
        elif self.conf.action == 'conf':
            self._sync_conf()
        else:
            self._cleanup()

    def _init_networks(self):

        self.networks = NetworksSet()
        self.networks.add('administration', self.conf.net_adm)
        self.networks.add('wan', self.conf.net_wan)
        self.networks.add('management', self.conf.net_mgt)
        self.networks.add('bmc', self.conf.net_bmc)

    def _parse_privatedata(self):

        logger.info("parsing privatedata")
        self._init_networks()
        self.privatedata = PrivateData(self.conf, self.networks)
        self.clusters = self.privatedata.parse()

    def _cleanup(self):

        logger.debug('running cleanup action')
        self.tmpdir = TmpDirManager(self.conf.dir_tmp)
        self.tmpdir.mrproper()
    #
    # certs methods
    #

    def _sync_certs(self):

        logger.debug('running sync certs action')
        self._parse_privatedata()
        for cluster in self.clusters:
            self._sync_certs_cluster(cluster)

        if self.all_certs_ok:
            logger.info('all certificates are OK')

    def _sync_certs_cluster(self, cluster):

        logger.debug("syncing certs for cluster %s", cluster.name)
        # substitute cluster name in dir ca from conf
        dir_crtdst = Template(self.conf.dir_crtdst)\
                       .safe_substitute(cluster=cluster.name)

        for equipment in cluster:
            self._sync_certs_equipment(cluster, equipment, dir_crtdst)

    def _sync_certs_equipment(self, cluster, equipment, dir_crtdst):

        if equipment.category != 'server' or \
           equipment.role in self.conf.nodes_roles:
            logger.debug("skipping equipment %s in certs sync", equipment.name)
            return

        # original CSR, certificate and key in icinga2 CA directory
        csr_file = os.path.join(self.conf.dir_ca, equipment.name + '.csr')
        crt_file = os.path.join(self.conf.dir_ca, equipment.name + '.crt')
        key_file = os.path.join(self.conf.dir_ca, equipment.name + '.key')

        # copy of certificate and encoded key in privatedata
        crtdst_file = os.path.join(dir_crtdst, equipment.name + '.crt')
        keydst_file = os.path.join(dir_crtdst, equipment.name + '.key.enc')

        logger.debug("checking if %s certificate/key files exist in %s",
                     equipment.name, dir_crtdst)
        if os.path.exists(crtdst_file) and os.path.exists(keydst_file):
            logger.debug("certificate already exist for %s", equipment.name)
            return

        self.all_certs_ok = False
        logger.info("creating new CSR, certificate and key for %s",
                    equipment.name)
        cmd = [ 'icinga2', 'pki', 'new-cert', '--cn', equipment.fqdn,
                '--csr', csr_file, '--key', key_file ]
        if not self.conf.dryrun:
            subprocess.check_call(cmd)

        cmd = [ 'icinga2', 'pki', 'sign-csr',
                '--csr', csr_file, '--cert', crt_file ]
        if not self.conf.dryrun:
            subprocess.check_call(cmd)

        logger.debug("copying crt %s to %s", crt_file, crtdst_file)
        if not self.conf.dryrun:
            shutil.copyfile(crt_file, crtdst_file)

        logger.debug("encoding key %s to %s", key_file, keydst_file)
        cmd = [ 'openssl', 'aes-256-cbc', '-in', key_file, '-out', keydst_file,
                '-k', self.keys.get(cluster.name) ]

        if not self.conf.dryrun:
            subprocess.check_call(cmd)

        logger.debug("setting strict mode on encoded key %s", keydst_file)
        if not self.conf.dryrun:
            os.chmod(keydst_file, 0400)

    #
    # conf methods
    #

    def _zone_dir(self, zone):
        
        return os.path.join(self.tmpdir.path, zone)

    def _load_template(self, name):

        tpl_loader = jinja2.FileSystemLoader(searchpath=self.conf.dir_templates)
        tpl_env = jinja2.Environment(loader=tpl_loader)
        tpl = name
        template = tpl_env.get_template(tpl)
        return template

    def _gen_zone_hosts(self, zone, hosts):

        os.makedirs(self._zone_dir(zone))
        hosts_file = os.path.join(self._zone_dir(zone), 'hosts.conf')
        logger.info("generating zone hosts file %s", hosts_file)

        tpl = self._load_template('hosts.conf')
        tpl_vars = { "hosts": hosts }

        with open(hosts_file, 'w+') as stream:
            stream.write(tpl.render(tpl_vars))

    def _gen_zone_zones(self, zone, hosts):

        zones_file = os.path.join(self._zone_dir(zone), 'zones.conf')
        logger.info("generating zone zones file %s", zones_file)

        tpl = self._load_template('zones.conf')
        tpl_vars = { "hosts": hosts,
                     "parent": zone }

        with open(zones_file, 'w+') as stream:
            stream.write(tpl.render(tpl_vars))

    def _copy_zone_conf(self, zone):

        zone_dir = os.path.join(self.conf.dir_conf, zone)
        dst_dir = os.path.join(self.tmpdir.path, zone)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        zone_files = os.listdir(zone_dir)
        for zone_file in zone_files:
            src_file = os.path.join(zone_dir, zone_file)
            dst_file = os.path.join(dst_dir, zone_file)
            logger.debug("copying %s into %s", src_file, dst_file)
            shutil.copyfile(src_file, dst_file)

    def _sync_conf(self):

        logger.debug('running sync conf action')

        self.tmpdir = TmpDirManager(self.conf.dir_tmp)
        self.tmpdir.make()

        self._parse_privatedata()
        self._sync_conf_master()
        for cluster in self.clusters:
            self._sync_conf_cluster(cluster)
        self._print_diff()

        if not self.conf.dryrun:
            self._copy_conf()

        self.tmpdir.clean()

        if not self.conf.dryrun:
            logger.info("check config with:")
            logger.info("# icinga2 daemon --validate --color")
            logger.info("reload icing2 with:")
            logger.info("# systemctl reload icinga2.service")

    def _sync_conf_master(self):

        hosts = []
        servers = []
        for cluster in self.clusters:
            for equipment in cluster:
                if equipment.monitored_by_master(self.conf.profs_master):
                    logger.debug("equipment %s must be monitored by master",
                                 equipment.name)
                    equipment.ip = equipment.get_ip_netif('wan')
                    equipment.set_attrs()
                    hosts.append(equipment)
                    if equipment.category == 'server' and \
                       not equipment.has_profile([self.conf.prof_monsat]):
                        servers.append(equipment)

        self._gen_zone_hosts('master', hosts)
        self._gen_zone_zones('master', servers)
        self._copy_zone_conf('master')
        self._copy_zone_conf('global-templates')

    def _sync_conf_cluster(self, cluster):

        hosts = []
        servers = []
        logger.debug("syncing conf for cluster %s", cluster.name)
        for equipment in cluster:
            if equipment.monitored_by_satellite(self.conf.profs_master,
                                                self.conf.nodes_roles):
                logger.debug("equipment %s is monitored by satellite",
                             equipment.name)

                admin_ip = equipment.get_ip_netif('administration')
                if admin_ip is not None:
                    equipment.ip = admin_ip
                else:
                    equipment.ip = equipment.get_ip_netif('management')

                equipment.set_attrs()

                hosts.append(equipment)
                if equipment.category == 'server':
                    servers.append(equipment)

        self._gen_zone_hosts(cluster.name, hosts)
        self._gen_zone_zones(cluster.name, servers)
        self._copy_zone_conf(cluster.name)

    def _print_diff(self):

        for root, directories, filenames in os.walk(self.tmpdir.path):
            for filename in filenames: 
                path = os.path.join(os.path.relpath(root, self.tmpdir.path),
                                    filename)
                src_file = os.path.join(self.tmpdir.path, path)
                dst_file = os.path.join(self.conf.dir_icinga2, 'zones.d', path)
                if not os.path.exists(dst_file):
                    logger.info("new file %s (%s does not exist)", path, dst_file)
                    continue
                self._print_diff_file(path, dst_file, src_file)

    def _print_diff_file(self, filename, fromfile, tofile):

        with open(fromfile) as stream:
            fromlines = stream.readlines()
        with open(tofile) as stream:
            tolines = stream.readlines()

        diff = difflib.unified_diff(fromlines, tolines, fromfile, tofile, n=3)
        # print diff
        sys.stdout.writelines(diff)

    def _copy_conf(self):

        entry = pwd.getpwnam(self.conf.conf_owner)
        uid = entry[2]
        gid = entry[3]

        for root, directories, filenames in os.walk(self.tmpdir.path):
            for filename in filenames: 
                path = os.path.join(os.path.relpath(root, self.tmpdir.path),
                                    filename)
                src_file = os.path.join(self.tmpdir.path, path)
                dst_file = os.path.join(self.conf.dir_icinga2, 'zones.d', path)
                logger.info("copying file %s to %s", src_file, dst_file)
                shutil.copyfile(src_file, dst_file)
                os.chown(dst_file, uid, gid)
                os.chmod(dst_file, 0644)
