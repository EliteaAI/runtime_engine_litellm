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

import requests  # pylint: disable=E0401


class LiteLLMClient:  # pylint: disable=R0904
    """ API client """

    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        #
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
        #
        self.timeout = 30

    def _endpoint(self, path):
        path_part = path.lstrip("/")
        return f"{self.base_url}/{path_part}"

    def _post_json(self, endpoint, data, timeout=...):
        result = self.session.post(
            self._endpoint(endpoint),
            json=data,
            timeout=self.timeout if timeout is ... else timeout,
        )
        #
        result.raise_for_status()
        #
        return result.json()

    def _get_json(self, endpoint, params=None, timeout=...):
        result = self.session.get(
            self._endpoint(endpoint),
            params=params,
            timeout=self.timeout if timeout is ... else timeout,
        )
        #
        result.raise_for_status()
        #
        return result.json()

    def _delete_json(self, endpoint, params=None, timeout=...):
        result = self.session.delete(
            self._endpoint(endpoint),
            params=params,
            timeout=self.timeout if timeout is ... else timeout,
        )
        #
        result.raise_for_status()
        #
        return result.json()

    #
    # Teams
    #

    def team_new(self, team_alias, models=None):
        """ Call """
        if models is None:
            models = [""]
        #
        return self._post_json(
            endpoint="/team/new",
            data={
                "team_alias": team_alias,
                "models": models,
            },
        )

    def team_update(self, team_id, updates):
        """ Call """
        return self._post_json(
            endpoint="/team/update",
            data={
                "team_id": team_id,
                **updates,
            },
        )

    def team_delete(self, team_id):
        """ Call """
        return self._post_json(
            endpoint="/team/delete",
            data={
                "team_ids": [team_id],
            },
        )

    def team_info(self, team_id):
        """ Call """
        return self._get_json(
            endpoint="/team/info",
            params={
                "team_id": team_id,
            },
        )

    def team_list(self, team_alias=None):
        """ Call """
        params = {}
        #
        if team_alias is not None:
            params["team_alias"] = team_alias
        #
        teams = []
        page = 1
        #
        while True:
            result = self._get_json(
                endpoint="/v2/team/list",
                params={
                    "page": page,
                    "page_size": 100,
                    **params,
                },
            )
            #
            teams.extend(result["teams"])
            #
            if page >= result["total_pages"]:
                break
            #
            page += 1
        #
        return teams

    def team_model_add(self, team_id, models):
        """ Call """
        return self._post_json(
            endpoint="/team/model/add",
            data={
                "team_id": team_id,
                "models": models,
            },
        )

    def team_model_delete(self, team_id, models):
        """ Call """
        return self._post_json(
            endpoint="/team/model/delete",
            data={
                "team_id": team_id,
                "models": models,
            },
        )

    #
    # Keys
    #

    def key_generate(self, key_alias, team_id, models=None):
        """ Call """
        data = {
            "key_alias": key_alias,
            "team_id": team_id,
        }
        #
        if models is not None:
            data["models"] = models
        #
        return self._post_json(
            endpoint="/key/generate",
            data=data,
        )

    def key_list(self, team_id=None):
        """ Call """
        params = {
            "return_full_object": True,
        }
        #
        if team_id is not None:
            params["team_id"] = team_id
        #
        keys = []
        page = 1
        #
        while True:
            result = self._get_json(
                endpoint="/key/list",
                params={
                    "page": page,
                    "size": 100,
                    **params,
                },
            )
            #
            keys.extend(result["keys"])
            #
            if page >= result["total_pages"]:
                break
            #
            page += 1
        #
        return keys

    def key_delete(self, key=None, key_alias=None):
        """ Call """
        data = {}
        #
        if key is not None:
            data["keys"] = [key]
        #
        if key_alias is not None:
            data["key_aliases"] = [key_alias]
        #
        return self._post_json(
            endpoint="/key/delete",
            data=data,
        )

    #
    # Models
    #

    def model_new(self, model_name, litellm_params, model_info=None):
        """ Call """
        if model_info is None:
            model_info = {}
        #
        return self._post_json(
            endpoint="/model/new",
            data={
                "model_name": model_name,
                "litellm_params": litellm_params,
                "model_info": model_info,
            },
        )

    def models(self, team_id=None):
        """ Call """
        return self._get_json(
            endpoint="/models",
            params={
                "team_id": team_id,
            } if team_id is not None else None,
        )["data"]

    def model_info(self, litellm_model_id=None):
        """ Call """
        return self._get_json(
            endpoint="/model/info",
            params={
                "litellm_model_id": litellm_model_id,
            } if litellm_model_id is not None else None,
        )["data"]

    def model_group_info(self, model_group=None):
        """ Call """
        return self._get_json(
            endpoint="/model_group/info",
            params={
                "model_group": model_group,
            } if model_group is not None else None,
        )["data"]

    def model_delete(self, model_id):
        """ Call """
        return self._post_json(
            endpoint="/model/delete",
            data={
                "id": model_id,
            },
        )

    #
    # Cache
    #

    def cache_flushall(self):
        """ Call """
        return self._post_json(
            endpoint="/cache/flushall",
            data=None,
        )

    #
    # Credentials
    #

    def credential_new(self, credential_name, credential_values, credential_info):
        """ Call """
        return self._post_json(
            endpoint="/credentials",
            data={
                "credential_name": credential_name,
                "credential_values": credential_values,
                "credential_info": credential_info,
            },
        )

    def credential_list(self):
        """ Call """
        return self._get_json(
            endpoint="/credentials",
        )["credentials"]

    def credential_delete(self, credential_name):
        """ Call """
        return self._delete_json(
            endpoint=f"/credentials/{credential_name}",
        )

    #
    # Health
    #

    def health_liveliness(self):
        """ Call """
        return self._get_json(
            endpoint="/health/liveliness",
        )

    def health_test_connection(self, litellm_params, mode=None, timeout=...):
        """ Call """
        data = {
            "litellm_params": litellm_params,
        }
        #
        if mode is not None:
            data["mode"] = mode
        #
        return self._post_json(
            endpoint="/health/test_connection",
            data=data,
            timeout=timeout,
        )

    #
    # Utils
    #

    def utils_token_counter(self, model, prompt=None, messages=None):
        """ Call """
        data = {
            "model": model,
        }
        #
        if prompt is not None:
            data["prompt"] = prompt
        #
        if messages is not None:
            data["messages"] = messages
        #
        return self._post_json(
            endpoint="/utils/token_counter",
            data=data,
        )
