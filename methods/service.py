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

import time

from pylon.core.tools import log  # pylint: disable=E0611,E0401,W0611
from pylon.core.tools import web  # pylint: disable=E0611,E0401,W0611

import requests  # pylint: disable=E0401

from tools import this  # pylint: disable=E0401


class Method:  # pylint: disable=E1101,R0903,W0201
    """
        Method Resource

        self is pointing to current Module instance

        web.method decorator takes zero or one argument: method name
        Note: web.method decorator must be the last decorator (at top)
    """

    @web.method()
    def runtime_wait(self):
        """ Method """
        #
        # Wait for liveness
        #
        liveness_start_ts = time.time()
        max_liveness_wait = this.descriptor.config.get("max_liveness_wait", 120)
        #
        while True:
            now_ts = time.time()
            #
            if now_ts - liveness_start_ts >= max_liveness_wait:
                raise RuntimeError("Service wait timeout exceeeded")
            #
            log.info("Waiting for service to start")
            #
            try:
                result = requests.get(
                    "http://127.0.0.1:8081/health/liveness",
                    timeout=(
                        this.descriptor.config.get("liveness_connect_timeout", 5),
                        this.descriptor.config.get("liveness_read_timeout", 5),
                    ),
                )
                #
                if result.status_code == 200:
                    break
                #
                raise RuntimeError("Service is still not up")
            except:  # pylint: disable=W0702
                time.sleep(this.descriptor.config.get("liveness_check_interval", 3))
