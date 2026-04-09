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

import io
import threading

import requests  # pylint: disable=E0401

from pylon.core.tools import log  # pylint: disable=E0611,E0401,W0611
from pylon.core.tools import web  # pylint: disable=E0611,E0401,W0611

from tools import this  # pylint: disable=E0401


class RequestThread(threading.Thread):  # pylint: disable=R0903
    """ Watch running process """

    def __init__(self, stream_node, input_stream_id, output_stream_id):
        super().__init__(daemon=True)
        #
        self.stream_node = stream_node
        #
        self.input_stream_id = input_stream_id
        self.output_stream_id = output_stream_id

    def run(self):
        """ Run thread """
        config = this.module.runtime_config()
        #
        emitter = self.stream_node.get_emitter(self.output_stream_id)
        consumer = self.stream_node.get_consumer(
            self.input_stream_id,
            timeout=this.descriptor.config.get("proxy_consumer_timeout", 600),
        )
        iterator = iter(consumer)
        #
        response = None
        #
        try:
            request = next(iterator)
            #
            if isinstance(request["files"], dict) and request["files"]:
                for key in list(request["files"]):
                    file_info = list(request["files"][key])
                    file_info[1] = io.BytesIO(file_info[1])
                    request["files"][key] = tuple(file_info)
                #
                # When files are present, remove Content-Type header so requests library
                # can generate its own with the correct boundary for multipart/form-data
                #
                headers = request.get("headers")
                if headers is not None:
                    # Convert to mutable dict if it's a werkzeug Headers object
                    if hasattr(headers, "to_wsgi_list"):
                        # It's a werkzeug Headers object
                        headers_dict = dict(headers)
                        if "Content-Type" in headers_dict:
                            del headers_dict["Content-Type"]
                        # Also remove Content-Length as it will change with new boundary
                        if "Content-Length" in headers_dict:
                            del headers_dict["Content-Length"]
                        request["headers"] = headers_dict
                    elif isinstance(headers, dict):
                        headers_lower = {k.lower(): k for k in headers}
                        if "content-type" in headers_lower:
                            del headers[headers_lower["content-type"]]
                        if "content-length" in headers_lower:
                            del headers[headers_lower["content-length"]]
                #
                # Convert ImmutableMultiDict to regular dict for form data
                #
                data = request.get("data")
                if data is not None and hasattr(data, "to_dict"):
                    # It's a werkzeug ImmutableMultiDict
                    request["data"] = data.to_dict(flat=True)
            #
            if config.get("litellm_mode") == "external" and config.get("external_litellm_url"):
                target_url = "/".join([
                    config["external_litellm_url"].rstrip("/"),
                    request["url"].lstrip("/"),
                ])
            else:
                target_url = "/".join([
                    "http://127.0.0.1:8081",
                    config['server_root_path'].strip("/"),
                    request["url"].lstrip("/"),
                ])
            #
            response = requests.request(
                method=request["method"],
                url=target_url,
                params=request["params"],
                headers=request["headers"],
                data=request["data"],
                json=request["json"],
                files=request["files"],
                stream=True,
                allow_redirects=False,
                verify=this.descriptor.config.get("proxy_ssl_verify", False),
                timeout=(
                    this.descriptor.config.get("proxy_connect_timeout", 100),
                    this.descriptor.config.get("proxy_read_timeout", 600),
                ),
            )
            #
            emitter.chunk({
                "headers": response.headers,
                "status_code": response.status_code,
            })
            #
            for chunk in response.iter_content(
                    chunk_size=this.descriptor.config.get("proxy_chunk_size", None),
            ):
                if chunk:
                    emitter.chunk(chunk)
        except BaseException as exception:  # pylint: disable=W0718
            emitter.exception(exception_info=str(exception))
        else:
            emitter.end()
        finally:
            if response is not None:
                response.close()
