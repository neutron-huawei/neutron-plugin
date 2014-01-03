# Copyright (c) 2013 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import threading

from oslo.config import cfg

from neutron import context as qcontext
from neutron.db import db_base_plugin_v2, external_net_db
from neutron.extensions import portbindings, external_net
from neutron.openstack.common import log as logging
from neutron.plugins.ml2.drivers.huawei import exceptions as ml2_exc
from neutron.plugins.ml2 import driver_api
from neutron.plugins.ml2.drivers.huawei import config
from neutron.plugins.ml2.drivers.huawei import clients
from neutron.plugins.ml2.drivers.huawei.clients import RemoteRestError


LOG = logging.getLogger(__name__)

sdn_UNREACHABLE_MSG = "Unable to reach sdn"
VXLAN_SEGMENTATION = "vxlan"


class HuaweiDriver(driver_api.MechanismDriver):
    """Ml2 Mechanism driver for Huawei networking hardware.

    Remebers all networks and VMs that are provisioned on Arista Hardware.
    Does not send network provisioning request if the network has already been
    provisioned before for the given port.
    """

    def __init__(self):
        confg = cfg.CONF.ml2_Huawei
        self.segmentation_type = VXLAN_SEGMENTATION
        self.timer = None
        self.db_base_plugin_v2 = db_base_plugin_v2.NeutronDbPluginV2()
        self.external_net_db = external_net_db.External_net_db_mixin()
        #         self.sdn = SyncService(self.rpc, self.ndb)
        self.sync_timeout = confg['sync_interval']
        self.cxt = qcontext.get_admin_context()
        self.sdn_sync_lock = threading.Lock()
        self.client_sdn = clients.SdnClient(confg.nos_host, confg.nos_port)

    def initialize(self):
        LOG.info("huawei driver instance build...")

    def create_network_postcommit(self, context):
        """Provision the network on the Huawei Hardware."""
        LOG.info("enter HuaweiDriver:create_network_postcommit()")
        network = context.current
        network_id = network['id']
        tenant_id = network['tenant_id']
        LOG.info("network_id = [%s] tenant_id = [%s]"
                 % (network_id, tenant_id))
        with self.sdn_sync_lock:
            try:
                mapped_network = self._get_mapped_network_with_subnets(
                    network)
                LOG.info("mapped_network = [%s]" % mapped_network)
                # create network on the network controller
                self.client_sdn.rest_create_network(tenant_id,
                                                    mapped_network)
            except RemoteRestError:
                LOG.error(sdn_UNREACHABLE_MSG)
                raise ml2_exc.MechanismDriverError(
                    method="create_network_postcommit")
            msg = _('Network %s is created') % network_id
            LOG.info(msg)

    def update_network_precommit(self, context):
        """At the moment we only support network name change

        Any other change in network is not supported at this time.
        We do not store the network names, therefore, no DB store
        action is performed here.
        """
        new_network = context.current
        orig_network = context.original
        if new_network['name'] != orig_network['name']:
            msg = _('Network name changed to %s') % new_network['name']
            LOG.info(msg)

    def update_network_postcommit(self, context):
        """At the moment we only support network name change

        If network name is changed, a new network create request is
        sent to the sdn controller.
        """
        new_network = context.current
        orig_network = context.original
        if new_network['name'] != orig_network['name']:
            network_id = new_network['id']
            with self.sdn_sync_lock:
                try:
                    self._send_update_network(new_network, context)
                except RemoteRestError:
                    LOG.error(sdn_UNREACHABLE_MSG)
                    raise ml2_exc.MechanismDriverError(
                        method="update_network_postcommit")
                msg = _('Network %s is updated') % network_id
                LOG.info(msg)

    def delete_network_postcommit(self, context):
        """Send network delete request to sdn controller."""
        network = context.current
        network_id = network['id']
        tenant_id = network['tenant_id']
        with self.sdn_sync_lock:

            # Succeed deleting network in case sdn is not accessible.
            # sdn state will be updated by sync thread once sdn gets
            # alive.
            try:
                self.client_sdn.rest_delete_network(tenant_id, network_id)
            except RemoteRestError:
                LOG.error(sdn_UNREACHABLE_MSG)
                raise ml2_exc.MechanismDriverError(
                    method="delete_network_postcommit")

    def create_port_postcommit(self, context):
        """Plug a physical host into a network.

        Send provisioning request to sdn controller to plug a host
        into appropriate network.
        """
        port = context.current
        device_id = port['device_id']
        device_owner = port['device_owner']
        host = port[portbindings.HOST_ID]

        # device_id and device_owner are set on VM boot
        is_vm_boot = device_id and device_owner
        if host and is_vm_boot:
            network_id = port['network_id']
            net = self.db_base_plugin_v2._get_network(self.cxt, network_id)
            try:
                self.client_sdn.rest_create_port(net, port)
            except RemoteRestError:
                LOG.error("create port %s on controller failed,reason:%s"
                          % (port['id'], sdn_UNREACHABLE_MSG))
                raise ml2_exc.MechanismDriverError(
                    method="create_port_postcommit")

            tenant_id = net["tenant_id"]
            net_id = net["id"]
            try:
                self.client_sdn.rest_plug_interface(tenant_id,
                                                    net_id,
                                                    port,
                                                    device_id)
            except RemoteRestError:
                LOG.error("plug interface %s to server %s failed,reason:%s"
                          % (port['id'], device_id, sdn_UNREACHABLE_MSG))
                raise ml2_exc.MechanismDriverError(
                    method="create_port_postcommit")

    def update_port_precommit(self, context):
        """Update the name of a given port.

        At the moment we only support port name change.
        Any other change to port is not supported at this time.
        We do not store the port names, therefore, no DB store
        action is performed here.
        """
        new_port = context.current
        orig_port = context.original
        if new_port['name'] != orig_port['name']:
            msg = _('Port name changed to %s') % new_port['name']
            LOG.info(msg)

    def update_port_postcommit(self, context):
        """Update the name of a given port in sdn.

        At the moment we only support port name change
        Any other change to port is not supported at this time.
        """
        port = context.current
        orig_port = context.original
        if port['name'] == orig_port['name']:
            # nothing to do
            return

    def delete_port_postcommit(self, context):
        """unPlug a physical host from a network."""
        port = context.current
        port_id = port['id']
        network_id = port['network_id']
        tenant_id = port['tenant_id']
        # only vm port should be deleted
        try:
            self.client_sdn.rest_delete_port(tenant_id,
                                             network_id,
                                             port_id)
        except RemoteRestError:
            LOG.error("delete port %s failed, reason:%s"
                      % (port_id, sdn_UNREACHABLE_MSG))
            raise ml2_exc.MechanismDriverError(
                method="delete_port_postcommit")

        try:
            self.client_sdn.rest_unplug_interface(tenant_id,
                                                  network_id,
                                                  port_id)
        except RemoteRestError:
            LOG.error("unplug interface %s failed, reason:%s"
                      % (port['id'], sdn_UNREACHABLE_MSG))
            raise ml2_exc.MechanismDriverError(
                method="delete_port_postcommit")

    def create_subnet_postcommit(self, context):

        subnet = context.current
        net_id = subnet['network_id']
        context = qcontext.get_admin_context()
        try:
            with self.sdn_sync_lock:
                orig_net = self.db_base_plugin_v2.get_network(context, net_id)
                # update network on network controller
                self._send_update_network(orig_net, context)
        except RemoteRestError:
            LOG.error(sdn_UNREACHABLE_MSG)
            raise ml2_exc.MechanismDriverError(
                method="create_subnet_postcommit")

    def update_subnet_postcommit(self, context):

        subnet = context.current
        net_id = subnet['network_id']
        try:
            with self.sdn_sync_lock:
                orig_net = self.db_base_plugin_v2.get_network(context, net_id)
                # update network on network controller
                self._send_update_network(orig_net, context)
        except RemoteRestError:
            LOG.error(sdn_UNREACHABLE_MSG)
            raise ml2_exc.MechanismDriverError(
                method="update_subnet_postcommit")

    def delete_subnet_postcommit(self, context):

        subnet = context.current
        net_id = subnet['network_id']
        try:
            with self.sdn_sync_lock:
                orig_net = self.db_base_plugin_v2.get_network(self.cxt, net_id)
                # update network on network controller
                self._send_update_network(orig_net, context)
        except RemoteRestError:
            LOG.error(sdn_UNREACHABLE_MSG)
            raise ml2_exc.MechanismDriverError(
                method="delete_subnet_postcommit")

    def _synchronization_thread(self):
        with self.sdn_sync_lock:
            self.sdn.synchronize()

        self.timer = threading.Timer(self.sync_timeout,
                                     self._synchronization_thread)
        self.timer.start()

    def stop_synchronization_thread(self):
        if self.timer:
            self.timer.cancel()
            self.timer = None

    def _get_mapped_network_with_subnets(self, network, context=None):
        # if context is not provided, admin context is used
        if context is None:
            context = qcontext.get_admin_context()
        network = self._map_state_and_status(network)
        subnets = self._get_all_subnets_json_for_network(network['id'],
                                                         context)
        network['subnets'] = subnets
        for subnet in (subnets or []):
            if subnet['gateway_ip']:
                # FIX: For backward compatibility with wire protocol
                network['gateway'] = subnet['gateway_ip']
                break
            else:
                network['gateway'] = ''
        network[
            external_net.EXTERNAL] = self.external_net_db.\
                                _network_is_external(context, network['id'])
        return network

    def _map_state_and_status(self, resource):
        resource = copy.copy(resource)

        resource['state'] = ('UP' if resource.pop('admin_state_up',
                                                  True) else 'DOWN')
        if 'status' in resource:
            del resource['status']
        return resource

    def _get_all_subnets_json_for_network(self, net_id, context=None):
        if context is None:
            context = qcontext.get_admin_context()
            # start a sub-transaction to avoid breaking parent transactions
        with context.session.begin(subtransactions=True):
            subnets = self.db_base_plugin_v2._get_subnets_by_network(context,
                                                                     net_id)
        subnets_details = []
        if subnets:
            for subnet in subnets:
                subnet_dict = self.db_base_plugin_v2._make_subnet_dict(subnet)
                mapped_subnet = self._map_state_and_status(subnet_dict)
                subnets_details.append(mapped_subnet)
        return subnets_details

    def _send_update_network(self, network, context):
        net_id = network['id']
        tenant_id = network['tenant_id']
        # update network on network controller
        mapped_network = self._get_mapped_network_with_subnets(network,
                                                               context)
        mapped_network['floatingips'] = []
        self.client_sdn.rest_update_network(tenant_id, net_id, mapped_network)
