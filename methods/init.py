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

from pylon.core.tools import log  # pylint: disable=E0611,E0401,W0611
from pylon.core.tools import web  # pylint: disable=E0611,E0401,W0611

import arbiter  # pylint: disable=E0401

from tools import worker_core  # pylint: disable=E0401

from ..tools.api import LiteLLMClient


class Method:  # pylint: disable=E1101,R0902,R0903,W0201
    """
        Method Resource

        self is pointing to current Module instance

        web.method decorator takes zero or one argument: method name
        Note: web.method decorator must be the last decorator (at top)
    """

    @web.init()
    def init(self):
        """ Init """
        config = self.runtime_config()
        #
        self.runtime_process = None
        self.runtime_watcher = None
        #
        if config.get("litellm_mode") == "external" and config.get("external_litellm_url"):
            log.info("Using external LiteLLM: %s", config["external_litellm_url"])
            # API calls go to the origin (no root path); proxy traffic uses the full URL
            from urllib.parse import urlparse, urlunparse  # pylint: disable=C0415
            parsed = urlparse(config["external_litellm_url"])
            self.api_base_url = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
        else:
            self.venv_create(config)
            self.venv_packages(config)
            #
            self.runtime_start()
            self.runtime_wait()
            #
            self.api_base_url = f"http://127.0.0.1:{config['litellm_port']}"
        #
        self.api_api_key = config["litellm_master_key"]
        self.api_client = LiteLLMClient(
            base_url=self.api_base_url,
            api_key=self.api_api_key,
        )
        #
        self.stream_node = arbiter.StreamNode(  # pylint: disable=I1101
            worker_core.event_node,
            id_prefix="litellm:",
        )
        self.service_node = arbiter.ServiceNode(  # pylint: disable=I1101
            worker_core.event_node,
            id_prefix="litellm:",
            default_timeout=30,
        )
        self.task_node = arbiter.TaskNode(  # pylint: disable=I1101
            worker_core.event_node,
            pool="litellm",
            task_limit=None,
            ident_prefix="litellm:",
            multiprocessing_context="threading",
            result_transport="memory",
            thread_scan_interval=1,
        )
        #
        self.stream_node.start()
        self.service_node.start()
        self.task_node.start()
        #
        self.service_node.register(
            self.litellm_request_start,
            "litellm_request_start",
        )
        #
        self.service_node.register(
            self.litellm_api_call,
            "litellm_api_call",
        )
        #
        self.service_node.register(
            self.litellm_delete_venv,
            "litellm_delete_venv",
        )
        #
        self.service_node.register(
            self.litellm_openai_invoke,
            "litellm_openai_invoke",
        )
        #
        self.task_node.register_task(
            self.litellm_openai_stream,
            "litellm_openai_stream",
        )
        #
        worker_core.event_node.emit(
            "runtime_engine_ready", {}
        )

    @web.deinit()
    def deinit(self):
        """ De-init """
        self.task_node.stop()
        self.service_node.stop()
        self.stream_node.stop()
        #
        self.runtime_stop()
