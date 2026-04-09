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
import subprocess

import yaml  # pylint: disable=E0401

from pylon.core.tools import log  # pylint: disable=E0611,E0401,W0611
from pylon.core.tools import web  # pylint: disable=E0611,E0401,W0611
from pylon.core.tools import process  # pylint: disable=E0611,E0401

from ..tools.watcher import ProcessWatcher


class Method:  # pylint: disable=E1101,R0903,W0201
    """
        Method Resource

        self is pointing to current Module instance

        web.method decorator takes zero or one argument: method name
        Note: web.method decorator must be the last decorator (at top)
    """

    @web.method()
    def runtime_running(self):
        """ Method """
        return self.runtime_process is not None and self.runtime_process.poll() is None

    @web.method()
    def runtime_start(self):
        """ Method """
        config = self.runtime_config()
        prisma_home = config["prisma_home"]
        bin_prisma = config["bin_prisma"]
        bin_litellm = config["bin_litellm"]
        #
        if not config["runtime_start"] or not os.path.exists(bin_litellm):
            return False
        #
        if self.runtime_process is not None and self.runtime_process.poll() is None:  # pylint: disable=E0203
            return True  # still running
        #
        pathlib.Path(prisma_home).mkdir(parents=True, exist_ok=True)
        #
        prisma_cache = os.path.join(prisma_home, ".cache")
        prisma_nodeenv = os.path.join(prisma_home, ".cache", "prisma-python", "nodeenv")
        #
        if not os.path.exists(prisma_cache) or not os.path.exists(prisma_nodeenv):
            try:
                from tools import this  # pylint: disable=E0401,C0415
                this.for_module("bootstrap").module.get_bundle(
                    "prisma-binaries.tar.gz",
                    processing="tar_extract",
                    extract_target=prisma_home,
                    extract_cleanup=False,
                )
                log.info("Using Prisma bundle")
            except:  # pylint: disable=W0702
                pass
        #
        prisma_schema = self.venv_find_prisma_schema(config)
        log.info("Generating prisma client: %s", prisma_schema)
        #
        target_env = os.environ.copy()
        target_env["PATH"] = os.pathsep.join([config["bin_path"], target_env["PATH"]])
        target_env["PRISMA_HOME_DIR"] = prisma_home
        target_env["PRISMA_NODEENV_CACHE_DIR"] = prisma_nodeenv
        target_env["HOME"] = prisma_home
        #
        if prisma_schema is not None:
            process.run_command(
                [
                    bin_prisma, "generate", "--schema", prisma_schema,
                ],
                env=target_env,
            )
        #
        target_env = os.environ.copy()
        target_env["PATH"] = os.pathsep.join([config["bin_path"], target_env["PATH"]])
        target_env["PRISMA_HOME_DIR"] = prisma_home
        target_env["PRISMA_NODEENV_CACHE_DIR"] = prisma_nodeenv
        target_env["HOME"] = prisma_home
        target_env["SERVER_ROOT_PATH"] = config["server_root_path"]
        target_env["LITELLM_MASTER_KEY"] = config["litellm_master_key"]
        target_env["DATABASE_URL"] = config["database_url"]
        target_env["STORE_MODEL_IN_DB"] = "True"
        #
        target_config = {
            "general_settings": {
                "store_model_in_db": True,
            },
            "litellm_settings": {
                "drop_params": True,
                "modify_params": True,
            },
            "environment_variables": {
                "MAX_IN_MEMORY_QUEUE_FLUSH_COUNT": "5000",
                "MAX_SIZE_IN_MEMORY_QUEUE": "500",
            },
        }
        #
        if config["log_request_response_data"]:
            target_config["general_settings"]["store_prompts_in_spend_logs"] = True
        #
        if config["enable_azure_ad_token_refresh"]:
            target_config["litellm_settings"]["enable_azure_ad_token_refresh"] = True
        #
        config_path = os.path.join(config["base_path"], "config.yml")
        #
        with open(config_path, "w", encoding="utf-8") as file:
            yaml.dump(target_config, file)
        #
        target_env["CONFIG_FILE_PATH"] = config_path
        #
        self.runtime_process = subprocess.Popen(  # pylint: disable=R1732
            args=[
                bin_litellm,
                "--host", config["litellm_host"],
                "--port", f"{config['litellm_port']}",
                "--drop_params",
                "--use_prisma_db_push",
            ],
            cwd=config["base_path"],
            env=target_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        #
        self.runtime_watcher = ProcessWatcher(self)
        self.runtime_watcher.start()
        #
        return True

    @web.method()
    def runtime_stop(self):
        """ Method """
        config = self.runtime_config()
        #
        if self.runtime_process is None:
            return True
        #
        if self.runtime_process.poll() is not None:
            return True
        #
        self.runtime_process.terminate()
        #
        try:
            self.runtime_process.communicate(timeout=config["runtime_stop_timeout"])
        except subprocess.TimeoutExpired:
            self.runtime_process.kill()
            self.runtime_process.communicate()
        #
        self.runtime_watcher.stop()
        self.runtime_watcher.join()
        #
        return True
