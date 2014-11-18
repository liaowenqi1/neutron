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


from oslo.config import cfg

""" Huawei ML2 Mechanism driver parameters.

Followings are connection parameters for Huawei ML2 Mechanism driver.
"""

HUAWEI_DRIVER_OPTS = [
    cfg.StrOpt('username',
               default='',
               help=_('Username for communications to Huawei Switch.'
                      'This is required field.')),
    cfg.StrOpt('password',
               default='',
               secret=True,
               help=_('Password for communications to Huawei Switch.'
                      'This is required field.')),
    cfg.StrOpt('hostaddr',
               default='',
               help=_('IP address of Huawei Switch.'
                      'This is required field.')),
    cfg.StrOpt('portname',
               default='',
               help=_('The name of port connection to Huawei Switch.'
                      'This is required field.'))
]

cfg.CONF.register_opts(HUAWEI_DRIVER_OPTS, "ml2_huawei")
