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
import tempfile
import shutil

class TmpDirManager(object):

    def __init__(self, parent):

        self.parent = parent
        self.path = None

    def make(self):

        """Make tmp generate dir and its parents."""
        if not os.path.isdir(self.parent):
            os.makedirs(self.parent)
        self.path = tempfile.mkdtemp(dir=self.parent)
        return self.path

    def clean(self):
        """Remove the run tmp dir."""

        logger.debug("removing run tmp dir %s", self.path)
        shutil.rmtree(self.path)

    def mrproper(self):
        """Remove the full app tmp dir."""
        if not os.path.isdir(self.parent):
            logger.info("app tmp dir %s does not exists, nothing to remove.", self.parent)
        else:
            logger.info("removing app tmp dir %s", self.parent)
            shutil.rmtree(self.parent)


