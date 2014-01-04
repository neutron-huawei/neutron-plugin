# vim: tabstop=4 shiftwidth=4 softtabstop=4
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

import mock

from neutron.plugins.ml2.drivers.huawei import clients as client
from neutron.plugins.ml2.drivers.huawei import exceptions as ml2_exc
from neutron.plugins.ml2.drivers.huawei import mechanism_huawei as huawei

from neutron.tests import base


class HuaweiDriverTestCase(base.BaseTestCase):
    """
        Test case for Huawei Ml2 driver
    """

    def setUp(self):
        super(HuaweiDriverTestCase, self).setUp()
        self.drv = huawei.HuaweiDriver()
        self.drv.client_sdn = mock.MagicMock()

    def test_create_network_on_valid_config(self):
        tenant_id = "tenant-1"
        network_id = "net-1"
        segmentation_id = 10001

        network_context = self._get_network_context(tenant_id,
                                                    network_id,
                                                    segmentation_id)

        net_info = network_context.current
        net_info["state"] = "UP"
        net_info["router:external"] = False
        net_info["subnets"] = []

        self.drv._get_mapped_network_with_subnets = mock.MagicMock()
        self.drv._get_mapped_network_with_subnets.return_value = net_info
        self.drv.client_sdn.rest_create_network
        self.drv.create_network_postcommit(network_context)
        self.drv.client_sdn.rest_create_network. \
            assert_called_once_with(tenant_id, net_info)

    def test_create_network_on_controller_fail(self):
        tenant_id = "tenant-1"
        network_id = "net-1"
        segmentation_id = 10001

        network_context = self._get_network_context(tenant_id,
                                                    network_id,
                                                    segmentation_id)
        net_info = network_context.current
        net_info["state"] = "UP"
        net_info["router:external"] = False
        net_info["subnets"] = []

        self.drv._get_mapped_network_with_subnets = mock.MagicMock()
        self.drv._get_mapped_network_with_subnets.return_value = net_info

        self.drv.client_sdn.rest_create_network = mock.MagicMock()
        self.drv.client_sdn.rest_create_network.side_effect = client\
            .RemoteRestError("controller unreachable")
        self.assertRaises(ml2_exc.MechanismDriverError,
                          self.drv.create_network_postcommit,
                          network_context)

    def test_update_network_on_valid_info(self):
        original_network = {"id": "net-1",
                            "tenant_id": "tenant-1",
                            "name": "net-name-1"}

        new_network = {"id": "net-1",
                       "tenant_id": "tenant-1",
                       "name": "net-name-2"}

        network_segments = [{"segmentation_id": 10001}]
        network_context = FakeNetworkContext(new_network,
                                             network_segments,
                                             original_network)
        net_info = network_context.current
        net_info["state"] = "UP"
        net_info["router:external"] = False
        net_info["subnets"] = []

        self.drv._get_mapped_network_with_subnets = mock.MagicMock()
        self.drv._get_mapped_network_with_subnets.return_value = net_info

        self.drv.update_network_postcommit(network_context)
        self.drv.client_sdn.rest_update_network. \
            assert_called_once_with("tenant-1", "net-1", net_info)

    def test_update_network_on_controller_fail(self):
        original_network = {"id": "net-1",
                            "tenant_id": "tenant-1",
                            "name": "net-name-1"}

        new_network = {"id": "net-1",
                       "tenant_id": "tenant-1",
                       "name": "net-name-2"}

        network_segments = [{"segmentation_id": 10001}]
        network_context = FakeNetworkContext(new_network,
                                             network_segments,
                                             original_network)
        net_info = network_context.current
        net_info["state"] = "UP"
        net_info["router:external"] = False
        net_info["subnets"] = []

        self.drv._get_mapped_network_with_subnets = mock.MagicMock()
        self.drv._get_mapped_network_with_subnets.return_value = net_info

        self.drv.update_network_postcommit(network_context)

        self.drv.client_sdn.rest_update_network = mock.MagicMock()
        self.drv.client_sdn.rest_update_network.side_effect = client\
            .RemoteRestError("controller unreachable")
        self.assertRaises(ml2_exc.MechanismDriverError,
                          self.drv.update_network_postcommit,
                          network_context)

    def test_delete_network_on_valid_info(self):
        tenant_id = "tenant-1"
        network_id = "net-1"
        segmentation_id = 10001
        network_context = self._get_network_context(tenant_id,
                                                    network_id,
                                                    segmentation_id)
        self.drv.delete_network_postcommit(network_context)
        self.drv.client_sdn.rest_delete_network. \
            assert_called_once_with(tenant_id, network_id)

    def test_delete_network_on_controller_fail(self):
        tenant_id = "tenant-1"
        network_id = "net-1"
        segmentation_id = 10001
        network_context = self._get_network_context(tenant_id,
                                                    network_id,
                                                    segmentation_id)

        self.drv.client_sdn.rest_delete_network = mock.MagicMock()
        self.drv.client_sdn.rest_delete_network.side_effect = client\
            .RemoteRestError("controller unreachable")
        self.assertRaises(ml2_exc.MechanismDriverError,
                          self.drv.delete_network_postcommit,
                          network_context)

    def test_create_port_on_valid_info(self):
        tenant_id = "tenant-1"
        network_id = "net-1"
        segmentation_id = 10001
        vm_id = "vm-1"
        network_context = self._get_network_context(tenant_id,
                                                    network_id,
                                                    segmentation_id)
        port_context = self._get_port_context(tenant_id,
                                              network_id,
                                              vm_id,
                                              network_context)
        net_info = network_context.current
        port_info = port_context.current
        self.drv.db_base_plugin_v2._get_network = mock.MagicMock()
        self.drv.db_base_plugin_v2._get_network.return_value = net_info

        self.drv.create_port_postcommit(port_context)

        self.drv.client_sdn.rest_create_port. \
            assert_called_once_with(net_info, port_info)
        self.drv.client_sdn.rest_plug_interface. \
            assert_called_once_with(tenant_id, network_id, port_info, vm_id)

    def test_create_port_on_controller_fail(self):
        tenant_id = "tenant-1"
        network_id = "net-1"
        segmentation_id = 10001
        vm_id = "vm-1"

        network_context = self._get_network_context(tenant_id,
                                                    network_id,
                                                    segmentation_id)
        port_context = self._get_port_context(tenant_id,
                                              network_id,
                                              vm_id,
                                              network_context)
        net_info = network_context.current
        self.drv.db_base_plugin_v2._get_network = mock.MagicMock()
        self.drv.db_base_plugin_v2._get_network.return_value = net_info

        self.drv.client_sdn.rest_create_port = mock.MagicMock()
        self.drv.client_sdn.rest_create_port.side_effect = client\
            .RemoteRestError("controller error")
        self.assertRaises(ml2_exc.MechanismDriverError,
                          self.drv.create_port_postcommit,
                          port_context)

    def test_create_port_on_plugin_port_fail(self):
        tenant_id = "tenant-1"
        network_id = "net-1"
        segmentation_id = 10001
        vm_id = "vm-1"

        network_context = self._get_network_context(tenant_id,
                                                    network_id,
                                                    segmentation_id)
        port_context = self._get_port_context(tenant_id,
                                              network_id,
                                              vm_id,
                                              network_context)
        net_info = network_context.current
        self.drv.db_base_plugin_v2._get_network = mock.MagicMock()
        self.drv.db_base_plugin_v2._get_network.return_value = net_info

        self.drv.client_sdn.rest_plug_interface = mock.MagicMock()
        self.drv.client_sdn.rest_plug_interface.side_effect = client\
            .RemoteRestError("controller plug port error")
        self.assertRaises(ml2_exc.MechanismDriverError,
                          self.drv.create_port_postcommit,
                          port_context)

    def test_delete_port_on_valid_info(self):
        tenant_id = "tenant-1"
        network_id = "net-1"
        segmentation_id = 10001
        vm_id = "vm-1"

        network_context = self._get_network_context(tenant_id,
                                                    network_id,
                                                    segmentation_id)
        port_context = self._get_port_context(tenant_id,
                                              network_id,
                                              vm_id,
                                              network_context)
        port_info = port_context.current
        self.drv.delete_port_postcommit(port_context)

        self.drv.client_sdn.rest_delete_port.\
            assert_called_once_with(tenant_id, network_id, port_info["id"])

        self.drv.client_sdn.rest_unplug_interface.\
            assert_called_once_with(tenant_id, network_id, port_info["id"])

    def test_delete_port_on_controller_fail(self):
        tenant_id = "tenant-1"
        network_id = "net-1"
        segmentation_id = 10001
        vm_id = "vm-1"

        network_context = self._get_network_context(tenant_id,
                                                    network_id,
                                                    segmentation_id)
        port_context = self._get_port_context(tenant_id,
                                              network_id,
                                              vm_id,
                                              network_context)

        self.drv.client_sdn.rest_delete_port = mock.MagicMock()
        self.drv.client_sdn.rest_delete_port.side_effect = client\
            .RemoteRestError("controller error")
        self.assertRaises(ml2_exc.MechanismDriverError,
                          self.drv.delete_port_postcommit,
                          port_context)

    def test_delete_port_on_unplug_port_error(self):
        tenant_id = "tenant-1"
        network_id = "net-1"
        segmentation_id = 10001
        vm_id = "vm-1"
        network_context = self._get_network_context(tenant_id,
                                                    network_id,
                                                    segmentation_id)
        port_context = self._get_port_context(tenant_id,
                                              network_id,
                                              vm_id,
                                              network_context)

        self.drv.client_sdn.rest_unplug_interface = mock.MagicMock()
        self.drv.client_sdn.rest_unplug_interface.side_effect = client\
            .RemoteRestError("controller unplug port error")
        self.assertRaises(ml2_exc.MechanismDriverError,
                          self.drv.delete_port_postcommit,
                          port_context)

    def test_create_subnet_on_valid_info(self):
        tenant_id = "tenant-1"
        network_id = "net-1"
        segmentation_id = 10001

        network_context = self._get_network_context(tenant_id,
                                                    network_id,
                                                    segmentation_id)
        subnet_context = self._get_subnet_context(tenant_id,
                                                  network_id)
        net_info = network_context.current
        self.drv.db_base_plugin_v2.get_network = mock.MagicMock()
        self.drv.db_base_plugin_v2.get_network.return_value = net_info

        net_info["state"] = "UP"
        net_info["router:external"] = False
        net_info["subnets"] = [subnet_context.current]

        self.drv._get_mapped_network_with_subnets = mock.MagicMock()
        self.drv._get_mapped_network_with_subnets.return_value = net_info

        self.drv.create_subnet_postcommit(subnet_context)
        self.drv.client_sdn.rest_update_network.\
            assert_called_once_with(tenant_id, network_id, net_info)

    def test_create_subnet_on_controller_fail(self):
        tenant_id = "tenant-1"
        network_id = "net-1"
        segmentation_id = 10001

        network_context = self._get_network_context(tenant_id,
                                                    network_id,
                                                    segmentation_id)
        subnet_context = self._get_subnet_context(tenant_id,
                                                  network_id)
        net_info = network_context.current
        self.drv.db_base_plugin_v2.get_network = mock.MagicMock()
        self.drv.db_base_plugin_v2.get_network.return_value = net_info

        net_info["state"] = "UP"
        net_info["router:external"] = False
        net_info["subnets"] = [subnet_context.current]

        self.drv._get_mapped_network_with_subnets = mock.MagicMock()
        self.drv._get_mapped_network_with_subnets.return_value = net_info

        self.drv.client_sdn.rest_update_network = mock.MagicMock()
        self.drv.client_sdn.rest_update_network.side_effect = client\
            .RemoteRestError("controller unplug port error")
        self.assertRaises(ml2_exc.MechanismDriverError,
                          self.drv.create_subnet_postcommit,
                          subnet_context)

    def test_update_subnet_on_valid_info(self):
        tenant_id = 'tenant-1'
        network_id = 'net-1'
        segmentation_id = 10001

        network_context = self._get_network_context(tenant_id,
                                                    network_id,
                                                    segmentation_id)
        subnet_context = self._get_subnet_context(tenant_id,
                                                  network_id)
        net_info = network_context.current

        self.drv.db_base_plugin_v2.get_network = mock.MagicMock()
        self.drv.db_base_plugin_v2.get_network.return_value = net_info

        net_info['state'] = 'UP'
        net_info['router:external'] = False
        net_info['subnets'] = [subnet_context.current]

        self.drv._get_mapped_network_with_subnets = mock.MagicMock()
        self.drv._get_mapped_network_with_subnets.return_value = net_info

        self.drv.update_subnet_postcommit(subnet_context)
        self.drv.client_sdn.rest_update_network.\
            assert_called_once_with(tenant_id, network_id, net_info)

    def test_update_subnet_on_controller_fail(self):
        tenant_id = "tenant-1"
        network_id = "net-1"
        segmentation_id = 10001

        network_context = self._get_network_context(tenant_id,
                                                    network_id,
                                                    segmentation_id)
        subnet_context = self._get_subnet_context(tenant_id,
                                                  network_id)
        net_info = network_context.current
        self.drv.db_base_plugin_v2.get_network = mock.MagicMock()
        self.drv.db_base_plugin_v2.get_network.return_value = net_info

        net_info["state"] = "UP"
        net_info["router:external"] = False
        net_info["subnets"] = [subnet_context.current]

        self.drv._get_mapped_network_with_subnets = mock.MagicMock()
        self.drv._get_mapped_network_with_subnets.return_value = net_info

        self.drv.client_sdn.rest_update_network = mock.MagicMock()
        self.drv.client_sdn.rest_update_network.side_effect = client\
            .RemoteRestError("controller unplug port error")
        self.assertRaises(ml2_exc.MechanismDriverError,
                          self.drv.create_subnet_postcommit,
                          subnet_context)

    def test_delete_subnet_on_valid_info(self):
        tenant_id = 'tenant-1'
        network_id = 'net-1'
        segmentation_id = 10001

        network_context = self._get_network_context(tenant_id,
                                                    network_id,
                                                    segmentation_id)
        subnet_context = self._get_subnet_context(tenant_id,
                                                  network_id)
        net_info = network_context.current
        self.drv.db_base_plugin_v2.get_network = mock.MagicMock()
        self.drv.db_base_plugin_v2.get_network.return_value = net_info

        net_info['state'] = 'UP'
        net_info['router:external'] = False
        net_info['subnets'] = []

        self.drv._get_mapped_network_with_subnets = mock.MagicMock()
        self.drv._get_mapped_network_with_subnets.return_value = net_info
        self.drv.delete_subnet_postcommit(subnet_context)
        self.drv.client_sdn.rest_update_network.\
            assert_called_once_with(tenant_id, network_id, net_info)

    def test_delete_subnet_on_controller_fail(self):
        tenant_id = 'tenant-1'
        network_id = 'net-1'
        segmentation_id = 10001

        network_context = self._get_network_context(tenant_id,
                                                    network_id,
                                                    segmentation_id)
        subnet_context = self._get_subnet_context(tenant_id,
                                                  network_id)
        net_info = network_context.current

        self.drv.db_base_plugin_v2.get_network = mock.MagicMock()
        self.drv.db_base_plugin_v2.get_network.return_value = net_info

        net_info['state'] = 'UP'
        net_info['router:external'] = False
        net_info['subnets'] = []

        self.drv._get_mapped_network_with_subnets = mock.MagicMock()
        self.drv._get_mapped_network_with_subnets.return_value = net_info

        self.drv.client_sdn.rest_update_network = mock.MagicMock()
        self.drv.client_sdn.rest_update_network.side_effect = client\
            .RemoteRestError("controller error")
        self.assertRaises(ml2_exc.MechanismDriverError,
                          self.drv.delete_subnet_postcommit,
                          subnet_context)

    def _get_network_context(self, tenant_id, net_id, seg_id):
        network = {"id": net_id,
                   "tenant_id": tenant_id}
        network_segments = [{"segmentation_id": seg_id}]
        return FakeNetworkContext(network, network_segments, network)

    def _get_port_context(self, tenant_id, net_id, vm_id, network):
        port = {"device_id": vm_id,
                "device_owner": "compute",
                "binding:host_id": "ubuntu1",
                "tenant_id": tenant_id,
                "id": 101,
                "network_id": net_id
        }
        return FakePortContext(port, port, network)

    def _get_subnet_context(self, tenant_id, net_id):
        subnet = {"name": "subnet-1",
                  "id": "subnet-id-1",
                  "ip_version": 4,
                  "cidr": "128.2.2.0/24",
                  "gateway_ip": "128.2.2.1",
                  "network_id": net_id,
                  "tenant_id": tenant_id
        }
        return FakeSubnetContext(subnet, subnet)


class FakeNetworkContext(object):
    """To generate network context for testing purposes only."""

    def __init__(self, network, segments=None, original_network=None):
        self._network = network
        self._original_network = original_network
        self._segments = segments

    @property
    def current(self):
        return self._network

    @property
    def original(self):
        return self._original_network

    @property
    def network_segments(self):
        return self._segments


class FakePortContext(object):
    """To generate port context for testing purposes only."""

    def __init__(self, port, original_port, network):
        self._port = port
        self._original_port = original_port
        self._network_context = network

    @property
    def current(self):
        return self._port

    @property
    def original(self):
        return self._original_port

    @property
    def network(self):
        return self._network_context


class FakeSubnetContext(object):
    """To generate subnet context for testing purposes only."""

    def __init__(self, subnet, original_subnet=None):
        self._subnet = subnet
        self._original_subnet = original_subnet

    @property
    def current(self):
        return self._subnet

    @property
    def original(self):
        return self._original_subnet
