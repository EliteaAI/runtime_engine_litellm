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

""" Method """

import os
import pathlib

from pylon.core.tools import log  # pylint: disable=E0611,E0401,W0611
from pylon.core.tools import web  # pylint: disable=E0611,E0401,W0611
from pylon.core.tools import process  # pylint: disable=E0611,E0401


class Method:  # pylint: disable=E1101,R0903,W0201
    """
        Method Resource

        self is pointing to current Module instance

        web.method decorator takes zero or one argument: method name
        Note: web.method decorator must be the last decorator (at top)
    """

    @web.method()
    def venv_create(self, config):
        """ Method """
        litellm_venv = config["litellm_venv"]
        bin_pip = config["bin_pip"]
        #
        if os.path.exists(bin_pip):
            return
        #
        pathlib.Path(litellm_venv).mkdir(parents=True, exist_ok=True)
        #
        log.info("Creating venv: %s", litellm_venv)
        #
        process.run_command(
            [
                "/usr/local/bin/python3", "-m", "venv", litellm_venv,
            ],
        )

    @web.method()
    def venv_find_prisma_schema(self, config):
        """ Method """
        litellm_venv = config["litellm_venv"]
        #
        for root, _, files in os.walk(litellm_venv):
            for name in files:
                if root.endswith("site-packages/litellm/proxy") and name == "schema.prisma":
                    return os.path.join(root, name)
        #
        return None


    @web.method()
    def apt_packages(self, packages):
        """ Install system packages required by LiteLLM (e.g. libsndfile1 for audio support). """
        if not packages:
            return
        #
        log.info("Installing system packages: %s", packages)
        #
        import subprocess  # pylint: disable=C0415
        env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
        try:
            subprocess.run(
                ["apt-get", "update", "-qq"],
                env=env,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["apt-get", "install", "-y", "--no-install-recommends"] + list(packages),
                env=env,
                check=True,
                capture_output=True,
            )
        except Exception as exc:  # pylint: disable=W0703
            log.warning("apt_packages: failed to install %s: %s", packages, exc)

    @web.method()
    def venv_packages(self, config):
        """ Method """
        bin_pip = config["bin_pip"]
        bin_litellm = config["bin_litellm"]
        #
        if os.path.exists(bin_litellm):
            return
        #
        c_args = []
        #
        try:
            index_url = self.context.module_manager.resolve_settings(
                "requirements.index_url", None
            )
            #
            if index_url is not None:
                c_args.append("--index-url")
                c_args.append(index_url)
            #
            trusted_hosts = self.context.module_manager.resolve_settings(
                "requirements.trusted_hosts", []
            )
            #
            for trusted_host in trusted_hosts:
                c_args.append("--trusted-host")
                c_args.append(trusted_host)
        except:  # pylint: disable=W0702
            pass
        #
        for package in config["litellm_packages"]:
            log.info("Installing package: %s", package)
            #
            process.run_command(
                [
                    bin_pip, "install", "-U", "--disable-pip-version-check",
                ] + c_args + [
                    package,
                ],
            )
