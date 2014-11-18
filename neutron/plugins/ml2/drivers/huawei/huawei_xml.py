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


HUAWEI_SWITCH_CREATE_VLAN = """
<config>
<vlan xmlns="http://www.huawei.com/netconf/vrp"content-version="1.0" format-version="1.0">
    <vlans>
        <vlan operation="create">
        <vlanId>%s</vlanId>
        <vlanName></vlanName>
        <vlanDesc></vlanDesc>
        <vlanType>common</vlanType>
        <vlanif>
        <cfgBand></cfgBand>
        <dampTime></dampTime>
        </vlanif>
        </vlan>
    </vlans>
</vlan>
</config>
"""


HUAWEI_SWITCH_DELETE_VLAN = """
<config>
<vlan xmlns="http://www.huawei.com/netconf/vrp"content-version="1.0" format-version="1.0">
    <vlans>
        <vlan operation="delete">
        <vlanId>%s</vlanId>
        <vlanName></vlanName>
        <vlanDesc></vlanDesc>
        <vlanType>common</vlanType>
        <vlanif>
        <cfgBand></cfgBand>
        <dampTime></dampTime>
        </vlanif>
        </vlan>
    </vlans>
</vlan>
</config>
"""


HUAWEI_SWITCH_CONFIG_PORT = """
<config>
<ethernet xmlns="http://www.huawei.com/netconf/vrp" content-version="1.0" format-version="1.0">
    <ethernetIfs>
        <ethernetIf operation="merge">
            <ifName>%s</ifName>
            <l2Attribute>
                <trunkVlans>%s:%s</trunkVlans>
            </l2Attribute>
        </ethernetIf>
    </ethernetIfs>
</ethernet>
</config>
"""


