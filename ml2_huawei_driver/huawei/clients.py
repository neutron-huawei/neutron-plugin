# Copyright 2012 Big Switch Networks, Inc.
# All Rights Reserved.
#
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
#
# @author: mayu, Huawei tech, Inc.

"""
A client for Huawei sdn controller.

"""

import base64
import httplib
import json
import socket

from oslo.config import cfg

from neutron.common import exceptions, utils
from neutron.openstack.common import log as logging


LOG = logging.getLogger(__name__)

restproxy_opts = [
    cfg.StrOpt('servers', default='localhost:8800',
               help=_("A comma separated server and port number ")),
    cfg.StrOpt('server_auth', default='username:password', secret=True,
               help=_("The username and password for authenticating "
                      "against the Huawei sdn controller.")),
    cfg.BoolOpt('server_ssl', default=False,
                help=_("If True, Use SSL when connecting to the "
                       "Huawei sdn controller ")),
    cfg.BoolOpt('sync_data', default=False,
                help=_("Sync data on connection")),
    cfg.IntOpt('server_timeout', default=10,
               help=_("Maximum number of seconds to wait for"
                      " proxy request to connect and complete.")),
]

cfg.CONF.register_opts(restproxy_opts, "RESTPROXY")

# The following are used to invoke the API on the external controller
NET_RESOURCE_PATH = "/tenants/%s/networks"
PORT_RESOURCE_PATH = "/tenants/%s/networks/%s/ports"
ROUTER_RESOURCE_PATH = "/tenants/%s/routers"
ROUTER_INTF_OP_PATH = "/tenants/%s/routers/%s/interfaces"
NETWORKS_PATH = "/tenants/%s/networks/%s"
PORTS_PATH = "/tenants/%s/networks/%s/ports/%s"
ATTACHMENT_PATH = "/tenants/%s/networks/%s/ports/%s/attachment"
ROUTERS_PATH = "/tenants/%s/routers/%s"
ROUTER_INTF_PATH = "/tenants/%s/routers/%s/interfaces/%s"
SUCCESS_CODES = range(200, 207)
FAILURE_CODES = [0, 301, 302, 303, 400, 401, 403, 404, 500, 501, 502, 503,
                 504, 505]
SYNTAX_ERROR_MESSAGE = _('Syntax error in server config file, aborting plugin')
BASE_URI = '/networkService/v1.1'
ORCHESTRATION_SERVICE_ID = 'Neutron v2.0'
METADATA_SERVER_IP = '169.254.169.254'


class RemoteRestError(exceptions.NeutronException):
    def __init__(self, message):
        if message is None:
            message = "None"
        self.message = _("Error in REST call to remote network "
                         "controller") + ": " + message
        super(RemoteRestError, self).__init__()


class ServerProxy(object):
    """REST server proxy to a network controller."""

    def __init__(self, server, port, ssl, auth, neutron_id, timeout,
                 base_uri, name):
        self.server = server
        self.port = port
        self.ssl = ssl
        self.base_uri = base_uri
        self.timeout = timeout
        self.name = name
        self.success_codes = SUCCESS_CODES
        self.auth = None
        self.neutron_id = neutron_id
        self.failed = False
        if auth:
            self.auth = 'Basic ' + base64.encodestring(auth).strip()

    def rest_call(self, action, resource, data, headers):
        uri = self.base_uri + resource
        body = json.dumps(data)
        if not headers:
            headers = {}
        headers['Content-type'] = 'application/json'
        headers['Accept'] = 'application/json'
        headers['NeutronProxy-Agent'] = self.name
        headers['Instance-ID'] = self.neutron_id
        headers['Orchestration-Service-ID'] = ORCHESTRATION_SERVICE_ID
        if self.auth:
            headers['Authorization'] = self.auth

        LOG.debug(_("ServerProxy: server=%(server)s, port=%(port)d, "
                    "ssl=%(ssl)r, action=%(action)s"),
                  {'server': self.server, 'port': self.port, 'ssl': self.ssl,
                   'action': action})
        LOG.debug(_("ServerProxy: resource=%(resource)s, data=%(data)r, "
                    "headers=%(headers)r"),
                  {'resource': resource, 'data': data, 'headers': headers})

        conn = None
        if self.ssl:
            conn = httplib.HTTPSConnection(
                self.server, self.port, timeout=self.timeout)
            if conn is None:
                LOG.error(_('ServerProxy: Could not establish HTTPS '
                            'connection'))
                return 0, None, None, None
        else:
            conn = httplib.HTTPConnection(
                self.server, self.port, timeout=self.timeout)
            if conn is None:
                LOG.error(_('ServerProxy: Could not establish HTTP '
                            'connection'))
                return 0, None, None, None

        try:
            conn.request(action, uri, body, headers)
            response = conn.getresponse()
            respstr = response.read()
            respdata = respstr
            if response.status in self.success_codes:
                try:
                    respdata = json.loads(respstr)
                except ValueError:
                    # response was not JSON, ignore the exception
                    pass
            ret = (response.status, response.reason, respstr, respdata)
        except (socket.timeout, socket.error) as e:
            LOG.error(_('ServerProxy: %(action)s failure, %(e)r'),
                      {'action': action, 'e': e})
            ret = 0, None, None, None
        conn.close()
        LOG.debug(_("ServerProxy: status=%(status)d, reason=%(reason)r, "
                    "ret=%(ret)s, data=%(data)r"), {'status': ret[0],
                                                    'reason': ret[1],
                                                    'ret': ret[2],
                                                    'data': ret[3]})
        return ret


class SdnClient(object):
    def __init__(self, server, port, ssl=None, auth=None, neutron_id=None,
                 timeout=10, base_uri='/networkService/v1.1',
                 name='NeutronRestProxy'):
        self.base_uri = base_uri
        self.timeout = timeout
        self.name = name
        self.auth = auth
        self.ssl = ssl
        self.neutron_id = neutron_id
        self.servers = []
        self.servers.append(self.server_proxy_for(server, port))

    def server_proxy_for(self, server, port):
        return ServerProxy(server, port, self.ssl, self.auth, self.neutron_id,
                           self.timeout, self.base_uri, self.name)

    def server_failure(self, resp, ignore_codes=[]):
        """Define failure codes as required.

        Note: We assume 301-303 is a failure, and try the next server in
        the server pool.
        """
        return (resp[0] in FAILURE_CODES and resp[0] not in ignore_codes)

    def action_success(self, resp):
        """Defining success codes as required.

        Note: We assume any valid 2xx as being successful response.
        """
        return resp[0] in SUCCESS_CODES

    @utils.synchronized('bsn-rest-call', external=True)
    def rest_call(self, action, resource, data, headers, ignore_codes):
        good_first = sorted(self.servers, key=lambda x: x.failed)
        for active_server in good_first:
            ret = active_server.rest_call(action, resource, data, headers)
            if not self.server_failure(ret, ignore_codes):
                active_server.failed = False
                return ret
            else:
                LOG.error(_('ServerProxy: %(action)s failure for servers: '
                            '%(server)r Response: %(response)s'),
                          {'action': action,
                           'server': (active_server.server,
                                      active_server.port),
                           'response': ret[3]})
                LOG.error(_("ServerProxy: Error details: status=%(status)d, "
                            "reason=%(reason)r, ret=%(ret)s, data=%(data)r"),
                          {'status': ret[0], 'reason': ret[1], 'ret': ret[2],
                           'data': ret[3]})
                active_server.failed = True

        # All servers failed, reset server list and try again next time
        LOG.error(_('ServerProxy: %(action)s failure for all servers: '
                    '%(server)r'),
                  {'action': action,
                   'server': tuple((s.server, s.port) for s in self.servers)})
        return (0, None, None, None)

    def rest_action(self, action, resource, data='', errstr='%s',
                    ignore_codes=[], headers=None):
        """
        Wrapper for rest_call that verifies success and raises a
        RemoteRestError on failure with a provided error string
        By default, 404 errors on DELETE calls are ignored because
        they already do not exist on the backend.
        """
        if not ignore_codes and action == 'DELETE':
            ignore_codes = [404]
        resp = self.rest_call(action, resource, data, headers, ignore_codes)
        if self.server_failure(resp, ignore_codes):
            LOG.error(_("NeutronRestProxyV2: ") + errstr, resp[2])
            raise RemoteRestError(resp[2])
        if resp[0] in ignore_codes:
            LOG.warning(_("NeutronRestProxyV2: Received and ignored error "
                          "code %(code)s on %(action)s action to resource "
                          "%(resource)s"),
                        {'code': resp[2], 'action': action,
                         'resource': resource})
        return resp

    def rest_create_network(self, tenant_id, network):
        resource = NET_RESOURCE_PATH % tenant_id
        data = {"network": network}
        errstr = _("Unable to create remote network: %s")
        self.rest_action('POST', resource, data, errstr)

    def rest_update_network(self, tenant_id, net_id, network):
        resource = NETWORKS_PATH % (tenant_id, net_id)
        data = {"network": network}
        errstr = _("Unable to update remote network: %s")
        self.rest_action('PUT', resource, data, errstr)

    def rest_delete_network(self, tenant_id, net_id):
        resource = NETWORKS_PATH % (tenant_id, net_id)
        errstr = _("Unable to update remote network: %s")
        self.rest_action('DELETE', resource, errstr)

    def rest_create_port(self, net, port):
        resource = PORT_RESOURCE_PATH % (net["tenant_id"], net["id"])
        data = {"port": port}
        errstr = _("Unable to create remote port: %s")
        self.rest_action('POST', resource, data, errstr)

    def rest_update_port(self, tenant_id, network_id, port, port_id):
        resource = PORTS_PATH % (tenant_id, network_id, port_id)
        data = {"port": port}
        errstr = _("Unable to update remote port: %s")
        self.rest_action('PUT', resource, data, errstr)

    def rest_delete_port(self, tenant_id, network_id, port_id):
        resource = PORTS_PATH % (tenant_id, network_id, port_id)
        errstr = _("Unable to delete remote port: %s")
        self.rest_action('DELETE', resource, errstr)

    def rest_plug_interface(self, tenant_id, net_id, port,
                            remote_interface_id):
        if port["mac_address"] is not None:
            resource = ATTACHMENT_PATH % (tenant_id, net_id, port["id"])
            data = {"attachment":
                    {
                        "id": remote_interface_id,
                        "mac": port["mac_address"]
                    }
                    }
            errstr = _("Unable to plug in interface: %s")
            self.rest_action('PUT', resource, data, errstr)

    def rest_unplug_interface(self, tenant_id, net_id, port_id):
        resource = ATTACHMENT_PATH % (tenant_id, net_id, port_id)
        errstr = _("Unable to unplug interface: %s")
        self.rest_action('DELETE', resource, errstr)
