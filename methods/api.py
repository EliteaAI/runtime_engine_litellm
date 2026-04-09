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
import json
import shutil
import importlib

from pylon.core.tools import log  # pylint: disable=E0611,E0401,W0611
from pylon.core.tools import web  # pylint: disable=E0611,E0401,W0611

from langchain_core.messages import (  # pylint: disable=E0401
    SystemMessage,
    HumanMessage,
    AIMessage,
)

from tools import worker_core  # pylint: disable=E0401


class Method:  # pylint: disable=E1101,R0903,W0201
    """
        Method Resource

        self is pointing to current Module instance

        web.method decorator takes zero or one argument: method name
        Note: web.method decorator must be the last decorator (at top)
    """

    @web.method()
    @worker_core.wrap_exceptions(RuntimeError)
    def litellm_api_call(self, method, *args, **kwargs):
        """ Method """
        api_method = getattr(self.api_client, method, None)
        #
        if api_method is None:
            raise RuntimeError("API method not found")
        #
        return api_method(*args, **kwargs)

    @web.method()
    @worker_core.wrap_exceptions(RuntimeError)
    def litellm_delete_venv(self):
        """ Method """
        config = self.runtime_config()
        litellm_venv = config["litellm_venv"]
        #
        try:
            if os.path.exists(litellm_venv):
                shutil.rmtree(litellm_venv)
            #
            log.info("Deleted venv")
        except:  # pylint: disable=W0702
            log.exception("Failed to delete venv")

    @web.method()
    def litellm_openai_resolve_target_method(  # pylint: disable=R0913,R0914
            self,
            target_class=None,
            target_args=None,
            target_kwargs=None,
            client_attr=None,
            method_name=None,
    ):
        """ Method """
        if target_class is None:
            raise RuntimeError("Target class not set")
        #
        if target_args is None:
            target_args = []
        #
        if target_kwargs is None:
            target_kwargs = {}
        #
        if "base_url" not in target_kwargs:
            target_kwargs["base_url"] = f'{self.api_base_url.rstrip("/")}/v1'
        #
        if "api_key" not in target_kwargs:
            target_kwargs["api_key"] = self.api_api_key
        #
        target_pkg, target_name = target_class.rsplit(".", 1)
        target_cls = getattr(
            importlib.import_module(target_pkg),
            target_name
        )
        #
        target = target_cls(*target_args, **target_kwargs)
        #
        if client_attr is None:
            client = target
        elif "." not in client_attr:
            client = getattr(target, client_attr)
        else:  # attr chain
            client = target
            #
            for attr in client_attr.split("."):
                client = getattr(client, attr)
        #
        if method_name is None:
            raise RuntimeError("Target method not set")
        #
        method = getattr(client, method_name)
        #
        return method

    @web.method()
    def convert_input_to_langchain(self, method_kwargs):
        """ Method """
        if "input" not in method_kwargs:
            return
        #
        result = []
        #
        for item in method_kwargs["input"]:
            if item["role"] == "system":
                result.append(SystemMessage(
                    content=item["content"],
                    name=item.get("name", None),
                ))
            elif item["role"] == "user":
                result.append(HumanMessage(
                    content=item["content"],
                    name=item.get("name", None),
                ))
            elif item["role"] == "assistant":
                result.append(AIMessage(
                    content=item["content"],
                    name=item.get("name", None),
                ))
            else:
                log.warning("Skipping unknown item: %s", item)
        #
        method_kwargs["input"] = result

    @web.method()
    @worker_core.wrap_exceptions(RuntimeError)
    def litellm_openai_invoke(  # pylint: disable=R0913,R0914
            self,
            target_class=None,
            target_args=None,
            target_kwargs=None,
            client_attr=None,
            method_name=None,
            method_args=None,
            method_kwargs=None,
            langchain_input=False,
            pydantic_cleanup=False,
    ):
        """ Method """
        method = self.litellm_openai_resolve_target_method(
            target_class, target_args, target_kwargs, client_attr, method_name
        )
        #
        if method_args is None:
            method_args = []
        #
        if method_kwargs is None:
            method_kwargs = {}
        #
        if langchain_input:
            self.convert_input_to_langchain(method_kwargs)
        #
        result = method(*method_args, **method_kwargs)
        #
        if pydantic_cleanup:
            result = json.loads(result.json())
        #
        return result

    @web.method()
    @worker_core.wrap_exceptions(RuntimeError)
    def litellm_openai_stream(  # pylint: disable=R0912,R0913,R0914
            self,
            stream_id,
            target_class=None,
            target_args=None,
            target_kwargs=None,
            client_attr=None,
            method_name=None,
            method_args=None,
            method_kwargs=None,
            langchain_input=False,
            pydantic_cleanup=False,
    ):
        """ Method """
        method = self.litellm_openai_resolve_target_method(
            target_class, target_args, target_kwargs, client_attr, method_name
        )
        #
        if method_args is None:
            method_args = []
        #
        if method_kwargs is None:
            method_kwargs = {}
        #
        if langchain_input:
            self.convert_input_to_langchain(method_kwargs)
        #
        emitter = self.stream_node.get_emitter(stream_id)
        #
        try:
            for chunk in method(*method_args, **method_kwargs):
                if pydantic_cleanup:
                    chunk = json.loads(chunk.json())
                #
                emitter.chunk(chunk)
        except BaseException as exception:  # pylint: disable=W0718
            emitter.exception(exception_info=str(exception))
        else:
            emitter.end()
