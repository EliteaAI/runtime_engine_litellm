#!/usr/bin/python3
# coding=utf-8

#   Copyright 2025 EPAM Systems
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

""" Module """

from pylon.core.tools import log  # pylint: disable=E0611,E0401,W0611
from pylon.core.tools import module  # pylint: disable=E0611,E0401,W0611


class Module(module.ModuleModel):  # pylint: disable=R0903
    """ Pylon module """

    def init(self):
        """ Initialize module """
        self.descriptor.init_all()

    def preload(self):
        """ Preload handler """
        self.descriptor.init_methods()
        #
        config = self.runtime_config()
        #
        self.venv_create(config)
        self.venv_packages(config)
        #
        import pathlib  # pylint: disable=C0415
        from tools import this  # pylint: disable=E0401,C0415
        #
        prisma_home = config["prisma_home"]
        pathlib.Path(prisma_home).mkdir(parents=True, exist_ok=True)
        #
        this.for_module("bootstrap").module.get_bundle(
            "prisma-binaries.tar.gz",
            processing="tar_extract",
            extract_target=prisma_home,
            extract_cleanup=False,
        )
