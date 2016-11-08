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

import argparse
import logging
logger = logging.getLogger(__name__)

def parse_args(conf):

    """Parses CLI args, then set debug flag and configuration file path in
       runtime configuration accordingly, and returns the args."""

    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices = ['certs', 'conf', 'cleanup'],
                        help='program action')
    parser.add_argument('-d', '--debug',
                        help='Enable debug mode',
                        action='store_true')
    parser.add_argument('--dry-run',
                        help='Dry run mode',
                        action='store_true')
    parser.add_argument('-c', '--conf',
                        help='Path to the configuration file',
                        nargs='?',
                        default='/etc/hpci2sync/conf.ini')

    args = parser.parse_args()

    if args.debug:
        conf.debug = True
    if args.dry_run:
        conf.dryrun = True
    if args.conf:
        conf.conf_file = args.conf

    conf.action = args.action

    return args

