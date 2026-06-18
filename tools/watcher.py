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

import logging
import threading

from pylon.core.tools import log  # pylint: disable=E0611,E0401,W0611
from pylon.core.tools import web  # pylint: disable=E0611,E0401,W0611


def _line_level(line: str) -> int:
    # Strip ANSI escapes cheaply (LiteLLM uses \x1b[...m colour codes)
    clean = line.replace('\x1b', '')
    prefix = clean[:50]
    if ':ERROR' in prefix or ':CRITICAL' in prefix:
        return logging.ERROR
    if ':WARNING' in prefix:
        return logging.WARNING
    return logging.DEBUG


class ProcessWatcher(threading.Thread):  # pylint: disable=R0903
    """ Watch running process """

    def __init__(self, module):
        super().__init__(daemon=True)
        #
        self.module = module
        self.stop_event = threading.Event()

    def run(self):
        """ Run thread """
        while not self.stop_event.is_set() and self.module.runtime_running():
            line = self.module.runtime_process.stdout.readline().decode().strip()
            #
            if line:
                log.log(_line_level(line), "%s", line)

    def stop(self):
        """ Request to stop """
        self.stop_event.set()
