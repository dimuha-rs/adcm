# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=wrong-import-position, unused-import, import-error
from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
sys.path.append('/adcm/python')
import adcm.init_django

from cm.ansible_plugin import ContextActionModule
from cm.api import (set_cluster_state, set_host_state, set_service_state,
                    set_service_state_by_id, set_provider_state)
from cm.status_api import Event

ANSIBLE_METADATA = {'metadata_version': '1.1', 'supported_by': 'Arenadata'}

DOCUMENTATION = r'''
---
module: adcm_state
short_description: Change state of object
description:
  - This is special ADCM only module which is usefull for seting state for various ADCM objects.
  - There is support of cluster, service, host and providers states
  - This one is allowed to be used in various execution contexts.
options:
  - option-name: type
    required: true
    choises:
      - cluster
      - service
      - provider
      - host
    description: type of object which should be changed

  - option-name: state
    required: true
    type: string
    description: value of state which should be set

  - option-name: service_name
    required: false
    type: string
    description: usefull in cluster context only. In that context you are able to set the state value for a service belongs to the cluster.

notes:
  - If type is 'service', there is no needs to specify service_name
'''

EXAMPLES = r'''
- adcm_state:
    type: "cluster"
    state: "statey"
  register: out
- adcm_state:
    type: "service"
    service_name: "First"
    state: "bimba!"
'''

RETURN = r'''
state:
  returned: success
  type: str
  example: "operational"
'''


class ActionModule(ContextActionModule):

    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(('type', 'service_name', 'state', 'host_id'))
    _MANDATORY_ARGS = ('type', 'state')

    def _do_cluster(self, task_vars, context):
        res = self._wrap_call(set_cluster_state, context['cluster_id'],
                              self._task.args["state"])
        res['state'] = self._task.args["state"]
        return res

    def _do_service_by_name(self, task_vars, context):
        res = self._wrap_call(set_service_state, context['cluster_id'],
                              self._task.args["service_name"],
                              self._task.args["state"])
        res['state'] = self._task.args["state"]
        return res

    def _do_service(self, task_vars, context):
        res = self._wrap_call(set_service_state_by_id, context['cluster_id'],
                              context['service_id'], self._task.args["state"])
        res['state'] = self._task.args["state"]
        return res

    def _do_host(self, task_vars, context):
        res = self._wrap_call(
            set_host_state,
            context['host_id'],
            self._task.args["state"],
        )
        res['state'] = self._task.args["state"]
        return res

    def _do_host_from_provider(self, task_vars, context):
        res = self._wrap_call(
            set_host_state,
            self._task.args['host_id'],
            self._task.args["state"],
        )
        res['state'] = self._task.args["state"]
        return res

    def _do_provider(self, task_vars, context):
        event = Event()
        res = self._wrap_call(set_provider_state, context['provider_id'],
                              self._task.args["state"], event)
        event.send_state()
        res['state'] = self._task.args["state"]
        return res
