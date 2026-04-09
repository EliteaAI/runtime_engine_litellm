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


class Method:  # pylint: disable=E1101,R0903,W0201
    """
        Method Resource

        self is pointing to current Module instance

        web.method decorator takes zero or one argument: method name
        Note: web.method decorator must be the last decorator (at top)
    """

    @web.method()
    def runtime_config(self):
        """ Method """
        config_maps = [
            lambda result: {
                "base_path": str(pathlib.Path(__file__).parent.parent.joinpath("data", "litellm")),
                "litellm_packages": [],
                #
                "runtime_start": True,
                "runtime_stop_timeout": 15,
                #
                "litellm_host": "127.0.0.1",
                "litellm_port": 8081,
                #
                "log_request_response_data": False,
                "enable_azure_ad_token_refresh": True,
            },
            lambda result: {
                "litellm_venv": os.path.join(result["base_path"], "venv"),
                "prisma_home": os.path.join(result["base_path"], "prisma"),
            },
            lambda result: {
                "bin_path": os.path.join(result["litellm_venv"], "bin"),
                "bin_pip": os.path.join(result["litellm_venv"], "bin", "pip3"),
                "bin_python": os.path.join(result["litellm_venv"], "bin", "python3"),
                "bin_prisma": os.path.join(result["litellm_venv"], "bin", "prisma"),
                "bin_litellm": os.path.join(result["litellm_venv"], "bin", "litellm"),
            },
        ]
        #
        result = {}
        #
        for config_map in config_maps:
            for key, default in config_map(result).items():
                result[key] = self.descriptor.config.get(key, default)
        #
        # Resolve database_url based on litellm_database_mode
        database_mode = self.descriptor.config.get("litellm_database_mode", "elitea")
        if database_mode == "elitea":
            from urllib.parse import urlparse, urlunparse  # pylint: disable=C0415
            litellm_db = self.descriptor.config.get("litellm_db_name", "litellm")
            #
            # Get base DB connection: prefer tools.config, fall back to env vars
            base_uri = None
            try:
                from tools import config as c  # pylint: disable=C0415,E0401
                base_uri = c.DATABASE_URI
            except (ImportError, RuntimeError):
                pass
            #
            if not base_uri:
                pg_user = os.environ.get("POSTGRES_USER")
                pg_password = os.environ.get("POSTGRES_PASSWORD")
                pg_host = os.environ.get("POSTGRES_HOST")
                pg_port = os.environ.get("POSTGRES_PORT", "5432")
                #
                if not all([pg_user, pg_password, pg_host]):
                    raise RuntimeError(
                        "litellm_database_mode is 'elitea' but neither tools.config "
                        "nor POSTGRES_* env vars are available"
                    )
                #
                base_uri = (
                    f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/placeholder"
                )
            #
            # Replace database name with litellm-specific one
            parsed = urlparse(base_uri)
            result["database_url"] = urlunparse(
                parsed._replace(path=f"/{litellm_db}")
            )
        else:
            db_url = self.descriptor.config.get("database_url")
            if not db_url:
                raise RuntimeError(
                    "litellm_database_mode is 'custom' but database_url is not set"
                )
            result["database_url"] = db_url
        #
        config_deps = [
            "litellm_master_key",
            "server_root_path",  # needed during litellm process start. NOTE: values from config are NOT automatically copied to result!
        ]
        #
        for key in config_deps:
            if key not in self.descriptor.config or self.descriptor.config[key] is None:
                raise RuntimeError(f"Required configuration value not set: {key}")
            #
            result[key] = self.descriptor.config[key]
        #
        result["litellm_mode"] = self.descriptor.config.get("litellm_mode", "built-in")
        result["external_litellm_url"] = self.descriptor.config.get("external_litellm_url", "")
        #
        return result
