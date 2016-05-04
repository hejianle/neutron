#!/usr/bin/env python
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import eventlet

from oslo_config import cfg
from oslo_log import log
from oslo_service import service as common_service

from neutron._i18n import _LI
from neutron import service

LOG = log.getLogger(__name__)


def eventlet_wsgi_server():
    neutron_api = service.serve_wsgi(service.NeutronApiService)
    start_api_and_rpc_workers(neutron_api)


def start_api_and_rpc_workers(neutron_api):
    try:
        plugin_workers_launcher = common_service.ProcessLauncher(
            cfg.CONF, wait_interval=1.0
        )
        service.start_rpc_workers(plugin_workers_launcher)

        pool = eventlet.GreenPool()
        api_thread = pool.spawn(neutron_api.wait)
        plugin_workers_thread = pool.spawn(plugin_workers_launcher.wait)

        # api and other workers should die together. When one dies,
        # kill the other.
        api_thread.link(lambda gt: plugin_workers_thread.kill())
        plugin_workers_thread.link(lambda gt: api_thread.kill())

        pool.waitall()
    except NotImplementedError:
        LOG.info(_LI("RPC was already started in parent process by "
                     "plugin."))

        neutron_api.wait()