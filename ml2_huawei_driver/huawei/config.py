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


""" Huawei ML2 Mechanism driver specific configuration knobs.

Following are user configurable options for Huawei ML2 Mechanism
driver. The eapi_username, eapi_password, and eapi_host are
required options. Region Name must be the same that is used by
Keystone service. This option is available to support multiple
OpenStack/Neutron controllers.
"""

from oslo.config import cfg


Huawei_DRIVER_OPTS = [
    cfg.StrOpt('nos_username',
               default='',
               help=_('Username for Huawei sdn controller. This is required field.'
                      'if not set, all communications to Huawei sdn controller'
                      'will fail')),
    cfg.StrOpt('nos_password',
               default='',
               secret=True,  # do not expose value in the logs
               help=_('Password for Huawei sdn controller. This is required field.'
                      'if not set, all communications to Huawei sdn controller'
                      'will fail')),
    cfg.StrOpt('nos_host',
               default='',
               help=_('Huawei sdn controller IP address. This is required field.'
                      'If not set, all communications to Huawei sdn controller'
                      'will fail')),
    cfg.IntOpt('nos_port',
               default='',
               help=_('Huawei sdn controller service port. This is required field.'
                      'If not set, all communications to Huawei sdn controller'
                      'will fail')),
    cfg.IntOpt('sync_interval',
               default=180,
               help=_('Sync interval in seconds between Neutron plugin and'
                      'sdn controller. This interval defines how often the'
                      'synchronization is performed. This is an optional'
                      'field. If not set, a value of 180 seconds is assumed'))
]

cfg.CONF.register_opts(Huawei_DRIVER_OPTS, "ml2_Huawei")
