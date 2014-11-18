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

import sys
import time
import struct
import threading

from oslo.config import cfg
from ncclient import manager

import sqlalchemy as sa
import neutron.db.api as db
from neutron.db import db_base_plugin_v2
from neutron.db import model_base
from neutron.db import models_v2

from neutron.common import exceptions
from neutron import context as neutron_context
from neutron.common import constants as neutron_const
from neutron.extensions import portbindings
from neutron.openstack.common import log as logging
from neutron.plugins.common import constants as plugin_const
from neutron.plugins.ml2.common import exceptions as ml2_except
from neutron.plugins.ml2 import driver_api
from neutron.plugins.ml2.drivers.huawei import config
from neutron.plugins.ml2.drivers.huawei import huawei_xml

LOG = logging.getLogger(__name__)

HUAWEI_SWITCH_UUID_LEN = 36
HUAWEI_SWITCH_STR_LEN  = 255


class HuaweiSwitchTenant(model_base.BASEV2, models_v2.HasId,
                                models_v2.HasTenant):
    """Save all tenants information into table.

    All Tenants list are saved.
    """
    __tablename__ = 'huawei_switch_tenant'
    
    def get_tenant_info(self):
        return {u'tenantId': self.tenant_id}

def add_tenant(tenant_id):
    """Add a tenant information into table.

    :param tenant_id: Neutron tenant identifier
    """
    session = db.get_session()
    with session.begin():
        tenant = HuaweiSwitchTenant(tenant_id=tenant_id)
        session.add(tenant)

def delete_tenant(tenant_id):
    """Delete a tenant information from table.

    :param tenant_id: Neutron tenant identifier
    """
    session = db.get_session()
    with session.begin():
        (session.query(HuaweiSwitchTenant).
         filter_by(tenant_id=tenant_id).
         delete())

def get_all_tenant():
    """Get all tenants information from table."""
    session = db.get_session()
    with session.begin():
        model = HuaweiSwitchTenant
        all_user = session.query(model)
        res = dict(
            (tenant.tenant_id, tenant.get_tenant_info())
            for tenant in all_user
        )
        return res

def delete_all_tenant(self, tenant_id):
    """Delete all tenants information from table.

    :param tenant_id: Neutron tenant identifier
    """        
    tenant_list = [tenant_id]
    
    for tenant in tenant_list:            
        tenant_obj = (get_network_count(tenant_id) +
                          get_vm_count(tenant_id))
        if not tenant_obj:
            delete_tenant(tenant_id)
        LOG.debug("delte a tenant %s", tenant)


class HuaweiSwitchVM(model_base.BASEV2, models_v2.HasId,
                            models_v2.HasTenant):
    """Save all VMs into table.

    All VMs launched on physical hosts connected to Huawei
    switches are saved.
    """
    __tablename__ = 'huawei_switch_vm'

    vm_id = sa.Column(sa.String(HUAWEI_SWITCH_STR_LEN))
    host_id = sa.Column(sa.String(HUAWEI_SWITCH_STR_LEN))
    port_id = sa.Column(sa.String(HUAWEI_SWITCH_UUID_LEN))
    network_id = sa.Column(sa.String(HUAWEI_SWITCH_UUID_LEN))

def add_vm(vm_id, host_id, port_id, network_id, tenant_id):
    """Add a VM into table.

    :param vm_id: VM instance identifier
    :param host_id: Identifier of the host where the VM is placed
    :param port_id: The port identifier that connects VM to network
    :param network_id: Neutron network identifier
    :param tenant_id: Neutron tenant identifier
    """
    session = db.get_session()
    with session.begin():
        vm = HuaweiSwitchVM(
            vm_id=vm_id,
            host_id=host_id,
            port_id=port_id,
            network_id=network_id,
            tenant_id=tenant_id)
        session.add(vm)

def delete_vm(vm_id, host_id, port_id, network_id, tenant_id):
    """Delete a tenant from table.

    :param vm_id: VM instance identifier
    :param host_id: Identifier of the host where the VM is placed
    :param port_id: The port identifier that connects VM to network
    :param network_id: Neutron network identifier
    :param tenant_id: Neutron tenant identifier
    """
    session = db.get_session()
    with session.begin():
        (session.query(HuaweiSwitchVM).
         filter_by(vm_id=vm_id, host_id=host_id,
                   port_id=port_id, tenant_id=tenant_id,
                   network_id=network_id).delete())

def is_exist_vm(vm_id, host_id, port_id,
                      network_id, tenant_id):
    """Check if a VM is already existed.

    :returns: True or False
    :param vm_id: VM instance identifier
    :param host_id: Identifier of the host where the VM is placed
    :param port_id: The port identifier that connects VM to network
    :param network_id: Neutron network identifier
    :param tenant_id: Neutron tenant identifier
    """
    session = db.get_session()
    with session.begin():
        num_vm = (session.query(HuaweiSwitchVM).
                  filter_by(tenant_id=tenant_id,
                            vm_id=vm_id,
                            port_id=port_id,
                            network_id=network_id,
                            host_id=host_id).count())
        return num_vm > 0

def get_vm_count(tenant_id):
    """Get number of VMs for a tenant.

    :param tenant_id: Neutron tenant identifier
    """
    session = db.get_session()
    with session.begin():
        return (session.query(HuaweiSwitchVM).
                filter_by(tenant_id=tenant_id).count())


class HuaweiSwitchNetwork(model_base.BASEV2, models_v2.HasId,
                                    models_v2.HasTenant):
    """Save all networks into table.

    All networks list are saved.
    Saves the segmentation identifier for each network
    that is provisioned.
    """
    __tablename__ = 'huawei_switch_network'

    network_id = sa.Column(sa.String(HUAWEI_SWITCH_UUID_LEN))
    segmentation_id = sa.Column(sa.Integer)

    def get_network_info(self, segmentation_type):
        return {u'networkId': self.network_id,
                u'segmentationTypeId': self.segmentation_id,
                u'segmentationType': segmentation_type}

def add_network(tenant_id, network_id, segmentation_id):
    """Add a network into table.

    :param tenant_id: Neutron tenant identifier
    :param network_id: Neutron network identifier
    :param segmentation_id: VLAN identifier
    """
    session = db.get_session()
    with session.begin():
        net = HuaweiSwitchNetwork(
            tenant_id=tenant_id,
            network_id=network_id,
            segmentation_id=segmentation_id)
        session.add(net)

def delete_network(tenant_id, network_id):
    """Delete a network from table.

    :param tenant_id: Neutron tenant identifier
    :param network_id: Neutron network identifier
    """
    session = db.get_session()
    with session.begin():
        (session.query(HuaweiSwitchNetwork).
         filter_by(tenant_id=tenant_id, network_id=network_id).
         delete())

def is_exist_network(tenant_id, network_id, segmentation_id=None):
    """Check if a network is already existed.

    :returns: True or False
    :param tenant_id: Neutron tenant identifier
    :param network_id: Neutron network identifier
    :param segmentation_id: VLAN identifier
    """
    session = db.get_session()
    with session.begin():
        if not segmentation_id:
            num_nets = (session.query(HuaweiSwitchNetwork).
                        filter_by(tenant_id=tenant_id,
                                  network_id=network_id).count())
        else:
            num_nets = (session.query(HuaweiSwitchNetwork).
                        filter_by(tenant_id=tenant_id,
                                  network_id=network_id,
                                  segmentation_id=segmentation_id).count())
        return num_nets > 0

def get_all_network(tenant_id):
    """Get all networks for a tenant.

    :param tenant_id: Neutron tenant identifier
    """
    session = db.get_session()
    with session.begin():
        model = HuaweiSwitchNetwork
        none = None
        all_network = (session.query(model).
                    filter(model.tenant_id == tenant_id,
                           model.segmentation_id != none))
        res = dict(
            (net.network_id, net.get_network_info(plugin_const.TYPE_VLAN))
            for net in all_network
        )
        return res

def get_network_count(tenant_id):
    """Get number of networks for a tenant.

    :param tenant_id: Neutron tenant identifier
    """
    session = db.get_session()
    with session.begin():
        return (session.query(HuaweiSwitchNetwork).
                filter_by(tenant_id=tenant_id).count())

def get_segment_id(tenant_id, network_id):
    """Get segmentation identifier.

    :param tenant_id: Neutron tenant identifier
    :param network_id: Neutron network identifier
    """
    session = db.get_session()
    with session.begin():
        net = (session.query(HuaweiSwitchNetwork).
               filter_by(tenant_id=tenant_id,
                         network_id=network_id).first())
        return net and net.segmentation_id or None


class HuaweiSwitchDriver(driver_api.MechanismDriver):
    """Huawei switch ML2 Mechanism Driver.

    Saved all networks and VMs provisioned on Huawei switch.
    NETCONF is used to connect to Huawei switch.
    Hardware of Huawei switch will be configured when networking information changed.
    """
    def __init__(self):
        self.connections = {}
        self.db_lock = threading.Lock()
        self.segmentation_type = plugin_const.TYPE_VLAN
        
        self.port = '22'
        self.host = self._get_host_addr()
        self.user = self._get_user_name()
        self.password = self._get_pass_word()
        self.user_port = self._get_port_name()
        self.vif_type = 'bridge'
        self.vif_details = {'vlan': True}
        self.neutron_network_db = HuaweiSwitchNeutronNetwork()

    def initialize(self):
        self.clear_database()

    def _connect(self, host):
        """Create SSH connection to the Huawei switch."""
        
        if getattr(self.connections.get(host), 'connected', None):
            return self.connections[host]        
        port = self.port
        user = self.user
        password = self.password        
        msg = _('Connect to Huawei switch successful.'
                'host:%s, user:%s, password:%s') % (host, user, password)
        LOG.debug(msg)
        
        try:
            conn = manager.connect(host=host,
                                  port=port,
                                  username=user,
                                  password=password,
                                  hostkey_verify=False,
                                  device_params={'name': "huawei"},
                                  timeout=30)
            self.connections[host] = conn
        except HuaweiSwitchConfigError:
            LOG.info("Failed to connect to switch.")
            raise ml2_except.MechanismDriverError
        return self.connections[host]

    def _config_switch(self, host, confstr):
        """Modify Huawei switch configuration information.

        :param host:   IP address of Huawei switch
        :param confstr: Configuration string in XML format
        :raises: HuaweiSwitchConfigFailed

        """
        manage = self._connect(host)
        
        try:
            msg = _('Modify switch configuration %s') % (confstr)
            LOG.debug(msg)
            
            con_obj = manage.edit_config(target='running', config=confstr)
            self._check_response(con_obj, "CREATE_VLAN")
        except HuaweiSwitchConfigError:
            LOG.info("Connect to switch failed.")
            raise ml2_except.MechanismDriverError
        return con_obj

    def _check_response(self, con_obj, xml_name):
        """Check if response message is already succeed."""
        LOG.debug("Reply for %s is %s" % (xml_name, con_obj.xml))
        xml_str = con_obj.xml
        if "<ok/>" in xml_str:
            LOG.info("%s successful" % xml_name)
        else:
            LOG.error("Execute: %s failed" % xml_name)

    def _get_host_addr(self):
        """Get IP address of Huawei switch."""
        if cfg.CONF.ml2_huawei.hostaddr == '':
            msg = _('Hostaddr is required.')
            LOG.error(msg)
            raise HuaweiSwitchConfigError(msg=msg)
        else:
            host_addr = cfg.CONF.ml2_huawei.hostaddr
        return host_addr

    def _get_user_name(self):
        """Get username for communications to Huawei switch."""
        if cfg.CONF.ml2_huawei.username == '':
            msg = _('Username is required.')
            LOG.error(msg)
            raise HuaweiSwitchConfigError(msg=msg)
        else:
            user_name = cfg.CONF.ml2_huawei.username
        return user_name

    def _get_pass_word(self):
        """Get password for communications to Huawei switch."""
        if cfg.CONF.ml2_huawei.password == '':
            msg = _('Password is required.')
            LOG.error(msg)
            raise HuaweiSwitchConfigError(msg=msg)
        else:
            pass_word = cfg.CONF.ml2_huawei.password
        return pass_word

    def _get_port_name(self):
        """Get name of port connection to Huawei switch."""
        if cfg.CONF.ml2_huawei.portname == '':
            msg = _('Portname is required.')
            LOG.error(msg)
            raise HuaweiSwitchConfigError(msg=msg)
        else:
            port_name = cfg.CONF.ml2_huawei.portname
        return port_name

    def create_network(self, tenant_id, network):
        """Creates a network on Huawei switch

        :param tenant_id: Neutron tenant identifier
        :param network: dict containing network_id, network_name and
                        segmentation_id
        """        
        LOG.debug("Create a network: %(network_id)s, %(segmentation_id)s, %(network_name)s",
                  {'network_id': network['network_id'],
                   'segmentation_id': network['segmentation_id'],
                   'network_name': network['network_name']})
        network_list = [network]
        
        for network in network_list:
            try:
                network_id = network['network_id']
                vlan_id = network['segmentation_id']
                network_name = network['network_name']
                confstr = huawei_xml.HUAWEI_SWITCH_CREATE_VLAN % (vlan_id)
                con_obj = self._config_switch(self.host,
                                            confstr=confstr)
                self._check_response(con_obj, "CREATE_VLAN")
            except HuaweiSwitchConfigError:
                LOG.exception("Exception in creating VLAN %s" % vlan_id)
                raise ml2_except.MechanismDriverError

    def delete_network(self, tenant_id, network):
        """Delete a network on Huawei switch

        :param tenant_id: Neutron tenant identifier
        :param network_id: Neutron network identifier
        """
        LOG.debug("Delete a network: %(network_id)s, %(segmentation_id)s, %(network_name)s",
                  {'network_id': network['network_id'],
                   'segmentation_id': network['segmentation_id'],
                   'network_name': network['network_name']})
        network_list = [network]
        
        for network in network_list:
            try:
                network_id = network['network_id']
                vlan_id = network['segmentation_id']
                network_name = network['network_name']
                confstr = huawei_xml.HUAWEI_SWITCH_DELETE_VLAN % (vlan_id)
                con_obj = self._config_switch(self.host,
                                            confstr=confstr)
                self._check_response(con_obj, "DELETE_VLAN")
            except HuaweiSwitchConfigError:
                LOG.exception("Exception in deleting VLAN %s" % vlan_id)
                raise ml2_except.MechanismDriverError

    def check_segment(self, segment):
        """Verify a segment is valid for Huawei switch driver."""
        
        return segment[driver_api.NETWORK_TYPE] in [plugin_const.TYPE_VLAN,
                                             plugin_const.TYPE_VXLAN]

    def add_port_into_network(self, vm_id, host_id, port_id,
                               network_id, tenant_id, port_name, device_owner):
        """Add a port of a VM instance into network.

        :param vm_id: VM instance identifier
        :param host_id: Identifier of the host where the VM is placed
        :param port_id: The port identifier that connects VM to network
        :param network_id: Neutron network identifier
        :param tenant_id: Neutron tenant identifier
        :param port_name: Name of the port
        :param device_owner: Device owner is compute or network
        """
        try:
            segmentation_id = get_segment_id(tenant_id,
                                                     network_id)
            vlan_id = segmentation_id
            bitmap = HuaweiSwitchVlanBitmap(neutron_const.MAX_VLAN_TAG + 2)
            bitmap.add_bitmap(vlan_id)
            
            confstring = bitmap.format_into_string()
            portid = self.user_port
            confstr = huawei_xml.HUAWEI_SWITCH_CONFIG_PORT % (portid, confstring, confstring)
            con_obj = self._config_switch(self.host,
                                        confstr=confstr)
            self._check_response(con_obj, "CONFIG_PORT")
        except HuaweiSwitchConfigError:
            LOG.exception("Exception in configing PORT %s, VLAN %s" % port_id, vlan_id)
            raise ml2_except.MechanismDriverError

    def delete_port_from_network(self, vm_id, host, port_id,
                                 network_id, tenant_id):
        """Delete a port of a VM instance from network.

        :param vm_id: VM instance identifier
        :param host: Identifier of the host where the VM is placed
        :param port_id: The port identifier that connects VM to network
        :param network_id: Neutron network identifier
        :param tenant_id: Neutron tenant identifier
        """
        try:
            segmentation_id = get_segment_id(tenant_id,
                                                     network_id)
            vlan_id = segmentation_id
            bitmap = HuaweiSwitchVlanBitmap(neutron_const.MAX_VLAN_TAG + 2)
            bitmap.delete_bitmap(vlan_id)
            
            confstring = bitmap.format_into_string()
            portid = self.user_port
            confstr = huawei_xml.HUAWEI_SWITCH_CONFIG_PORT % (portid, confstring, confstring)
            con_obj = self._config_switch(self.host,
                                        confstr=confstr)
            self._check_response(con_obj, "CONFIG_PORT")
        except HuaweiSwitchConfigError:
            LOG.exception("Exception in configing PORT %s, VLAN %s" % port_id, vlan_id)
            raise ml2_except.MechanismDriverError

    def create_network_precommit(self, context):
        """Allocate resources for a new network.

        :param context: NetworkContext instance describing the new
        network.

        Create a new network, allocating resources as necessary in the
        database. Called inside transaction context on session. Call
        cannot block.  Raising an exception will result in a rollback
        of the current transaction.
        """
        
        network = context.current
        segments = context.network_segments
        network_id = network['id']
        tenant_id = network['tenant_id']
        segmentation_id = segments[0]['segmentation_id']
        
        with self.db_lock:
            add_tenant(tenant_id)
            add_network(tenant_id,
                                network_id,
                                segmentation_id)
            segmentation_id = get_segment_id(tenant_id,
                                                     network_id)
            msg = _('Create network precommit. tenant_id:%s, network_id:%s'
                    'segmentation_id:%s') % (tenant_id, network_id, segmentation_id)
            LOG.debug(msg)

    def create_network_postcommit(self, context):
        """Create a network.

        :param context: NetworkContext instance describing the new
        network.

        Called after the transaction commits. Call can block, though
        will block the entire process so care should be taken to not
        drastically affect performance. Raising an exception will
        cause the deletion of the resource.
        """
        
        network = context.current
        network_id = network['id']
        network_name = network['name']
        tenant_id = network['tenant_id']
        segments = context.network_segments
        vlan_id = segments[0]['segmentation_id']
        msg = _('Create network postcommit. tenant_id:%s, network_id:%s'
                'vlan_id:%s') % (tenant_id, network_id, vlan_id)                
        LOG.debug(msg)
        
        with self.db_lock:
            if is_exist_network(tenant_id, network_id):
                try:
                    network_dict = {
                        'network_id': network_id,
                        'segmentation_id': vlan_id,
                        'network_name': network_name}
                    self.create_network(tenant_id, network_dict)
                except HuaweiSwitchConfigError:
                    LOG.info("Failed to connect to switch.")
                    raise ml2_except.MechanismDriverError()
            else:
                msg = _('Network %s is not created as it is not found in'
                        'Huawei DB') % (network_id)
                LOG.info(msg)

    def update_network_precommit(self, context):
        """Update resources of a network.

        :param context: NetworkContext instance describing the new
        state of the network, as well as the original state prior
        to the update_network call.

        Update values of a network, updating the associated resources
        in the database. Called inside transaction context on session.
        Raising an exception will result in rollback of the
        transaction.

        update_network_precommit is called for all changes to the
        network state. It is up to the mechanism driver to ignore
        state or state changes that it does not know or care about.
        """
        
        new_network = context.current
        old_network = context.original
        LOG.debug("Upadate a new network: %(network_id)s, %(segmentation_id)s, %(network_name)s",
                  {'network_id': new_network['network_id'],
                   'segmentation_id': new_network['segmentation_id'],
                   'network_name': new_network['network_name']})
        LOG.debug("Upadate a old network: %(network_id)s, %(segmentation_id)s, %(network_name)s",
                  {'network_id': old_network['network_id'],
                   'segmentation_id': old_network['segmentation_id'],
                   'network_name': old_network['network_name']})
        if new_network['name'] != old_network['name']:
            msg = _('Network name changed to %s') % new_network['name']
            LOG.info(msg)

    def update_network_postcommit(self, context):
        """Update a network.

        :param context: NetworkContext instance describing the new
        state of the network, as well as the original state prior
        to the update_network call.

        Called after the transaction commits. Call can block, though
        will block the entire process so care should be taken to not
        drastically affect performance. Raising an exception will
        cause the deletion of the resource.

        update_network_postcommit is called for all changes to the
        network state.  It is up to the mechanism driver to ignore
        state or state changes that it does not know or care about.
        """
        
        new_network = context.current
        old_network = context.original
        if new_network['name'] != old_network['name']:
            network_id = new_network['id']
            network_name = new_network['name']
            tenant_id = new_network['tenant_id']
            vlan_id = new_network['provider:segmentation_id']
            with self.db_lock:
                if is_exist_network(tenant_id, network_id):
                    try:
                        network_dict = {
                            'network_id': network_id,
                            'segmentation_id': vlan_id,
                            'network_name': network_name}
                        self.create_network(tenant_id, network_dict)
                    except HuaweiSwitchConfigError:
                        LOG.info("Failed to connect to switch.")
                        raise ml2_except.MechanismDriverError()
                else:
                    msg = _('Network %s is not updated as it is not found in'
                            'Huawei DB') % (network_id)
                    LOG.info(msg)

    def delete_network_precommit(self, context):
        """Delete resources for a network.

        :param context: NetworkContext instance describing the current
        state of the network, prior to the call to delete it.

        Delete network resources previously allocated by this
        mechanism driver for a network. Called inside transaction
        context on session. Runtime errors are not expected, but
        raising an exception will result in rollback of the
        transaction.
        """
        
        network = context.current
        network_id = network['id']
        tenant_id = network['tenant_id']
        segments = context.network_segments
        LOG.debug("Delete a network: %(network_id)s, %(segmentation_id)s, %(network_name)s",
                  {'network_id': network['network_id'],
                   'segmentation_id': segments[0]['segmentation_id'],
                   'network_name': network['network_name']})
        with self.db_lock:
            if is_exist_network(tenant_id, network_id):
                delete_network(tenant_id, network_id)
            delete_all_tenant(tenant_id)

    def delete_network_postcommit(self, context):
        """Delete a network.

        :param context: NetworkContext instance describing the current
        state of the network, prior to the call to delete it.

        Called after the transaction commits. Call can block, though
        will block the entire process so care should be taken to not
        drastically affect performance. Runtime errors are not
        expected, and will not prevent the resource from being
        deleted.
        """
        
        network = context.current
        network_id = network['id']
        network_name = network['name']
        tenant_id = network['tenant_id']
        segments = context.network_segments
        vlan_id = segments[0]['segmentation_id']
        with self.db_lock:
            try:
                network_dict = {
                    'network_id': network_id,
                    'segmentation_id': vlan_id,
                    'network_name': network_name}
                self.delete_network(tenant_id, network_dict)
            except HuaweiSwitchConfigError:
                LOG.info("Failed to connect to switch.")
                raise ml2_except.MechanismDriverError()

    def create_port_precommit(self, context):
        """Allocate resources for a new port.

        :param context: PortContext instance describing the port.

        Create a new port, allocating resources as necessary in the
        database. Called inside transaction context on session. Call
        cannot block.  Raising an exception will result in a rollback
        of the current transaction.
        """
        
        port = context.current
        device_id = port['device_id']
        device_owner = port['device_owner'] 
        host = context.host
        
        port_id = port['id']
        network_id = port['network_id']
        tenant_id = port['tenant_id']
        segmentation_id = get_segment_id(tenant_id,
                                                 network_id)
        msg = _('Create a port precommit. host:%s, port_id:%s, network_id:%s, tenant_id:%s'
                'vlan_id:%s') % (host, port_id, network_id, tenant_id, segmentation_id)            
        LOG.debug(msg)
        
        is_vm_boot = device_id and device_owner
        if host and is_vm_boot:
            port_id = port['id']
            network_id = port['network_id']
            tenant_id = port['tenant_id']
            with self.db_lock:
                add_vm(device_id, host, port_id,
                               network_id, tenant_id)

    def create_port_postcommit(self, context):
        """Create a port.

        :param context: PortContext instance describing the port.

        Called after the transaction completes. Call can block, though
        will block the entire process so care should be taken to not
        drastically affect performance.  Raising an exception will
        result in the deletion of the resource.
        """
        
        port = context.current
        device_id = port['device_id']
        device_owner = port['device_owner']
        
        host = context.host
        is_vm_boot = device_id and device_owner
        if host and is_vm_boot:
            port_id = port['id']
            port_name = port['name']
            network_id = port['network_id']
            tenant_id = port['tenant_id']
            with self.db_lock:
                hostname = self._host_name(host)
                vm = is_exist_vm(device_id,
                                            host,
                                            port_id,
                                            network_id,
                                            tenant_id)
                net = is_exist_network(tenant_id,
                                            network_id)
                if vm and net:
                    try:
                        segmentation_id = get_segment_id(tenant_id,
                                                                 network_id)
                        msg = _('Create a port postcommit. host:%s, port_id:%s, network_id:%s, tenant_id:%s'
                                'vlan_id:%s') % (host, port_id, network_id, tenant_id, segmentation_id)
                        LOG.debug(msg)
                        
                        self.add_port_into_network(device_id,
                                                    hostname,
                                                    port_id,
                                                    network_id,
                                                    tenant_id,
                                                    port_name,
                                                    device_owner)
                    except HuaweiSwitchConfigError:
                        LOG.info("Failed to connect to switch.")
                        raise ml2_except.MechanismDriverError()
                else:
                    msg = _('VM %s is not created as it is not found in '
                            'Huawei DB') % device_id
                    LOG.info(msg)

    def update_port_precommit(self, context):
        """Update resources of a port.

        :param context: PortContext instance describing the new
        state of the port, as well as the original state prior
        to the update_port call.

        Called inside transaction context on session to complete a
        port update as defined by this mechanism driver. Raising an
        exception will result in rollback of the transaction.

        update_port_precommit is called for all changes to the port
        state. It is up to the mechanism driver to ignore state or
        state changes that it does not know or care about.
        """
        
        msg = _('Update a port precommit')
        LOG.debug(msg)

    def update_port_postcommit(self, context):
        """Update a port.

        :param context: PortContext instance describing the new
        state of the port, as well as the original state prior
        to the update_port call.

        Called after the transaction completes. Call can block, though
        will block the entire process so care should be taken to not
        drastically affect performance.  Raising an exception will
        result in the deletion of the resource.

        update_port_postcommit is called for all changes to the port
        state. It is up to the mechanism driver to ignore state or
        state changes that it does not know or care about.
        """
        
        port = context.current
        old_port = context.original
        msg = _('Update a port postcommit')
        LOG.debug(msg)
        
        if port['name'] == old_port['name']:
            return
        device_id = port['device_id']
        device_owner = port['device_owner']        
        host = context.host
        is_vm_boot = device_id and device_owner
        
        if host and is_vm_boot:
            port_id = port['id']
            port_name = port['name']
            network_id = port['network_id']
            tenant_id = port['tenant_id']
            with self.db_lock:
                hostname = self._host_name(host)
                segmentation_id = get_segment_id(tenant_id,
                                                         network_id)
                vm = is_exist_vm(device_id,
                                            host,
                                            port_id,
                                            network_id,
                                            tenant_id)
                net = is_exist_network(tenant_id,
                                            network_id,
                                            segmentation_id)
                if vm and net:
                    try:
                        self.add_port_into_network(device_id,
                                                    hostname,
                                                    port_id,
                                                    network_id,
                                                    tenant_id,
                                                    port_name,
                                                    device_owner)
                    except HuaweiSwitchConfigError:
                        LOG.info("Failed to connect to switch.")
                        raise ml2_except.MechanismDriverError()
                else:
                    msg = _('VM %s is not updated as it is not found in '
                            'Huawei DB') % device_id
                    LOG.info(msg)

    def delete_port_precommit(self, context):
        """Delete resources of a port.

        :param context: PortContext instance describing the current
        state of the port, prior to the call to delete it.

        Called inside transaction context on session. Runtime errors
        are not expected, but raising an exception will result in
        rollback of the transaction.
        """
        
        port = context.current
        device_id = port['device_id']
        host_id = context.host
        tenant_id = port['tenant_id']
        network_id = port['network_id']
        port_id = port['id']
        
        segmentation_id = get_segment_id(tenant_id,
                                                 network_id)
        msg = _('Delete a port precommit. host:%s, port_id:%s, network_id:%s, tenant_id:%s'
                'vlan_id:%s') % (host_id, port_id, network_id, tenant_id, segmentation_id)
        LOG.debug(msg)
        
        with self.db_lock:
            if is_exist_vm(device_id, host_id, port_id,
                                    network_id, tenant_id):
                delete_vm(device_id, host_id, port_id,
                             network_id, tenant_id)
            delete_all_tenant(tenant_id)

    def delete_port_postcommit(self, context):
        """Delete a port.

        :param context: PortContext instance describing the current
        state of the port, prior to the call to delete it.

        Called after the transaction completes. Call can block, though
        will block the entire process so care should be taken to not
        drastically affect performance.  Runtime errors are not
        expected, and will not prevent the resource from being
        deleted.
        """
        
        port = context.current
        device_id = port['device_id']
        host = context.host
        port_id = port['id']
        network_id = port['network_id']
        tenant_id = port['tenant_id']
        device_owner = port['device_owner']
        
        try:
            with self.db_lock:
                hostname = self._host_name(host)
                self.delete_port_from_network(device_id,
                                               hostname,
                                               port_id,
                                               network_id,
                                               tenant_id)
        except HuaweiSwitchConfigError:
            LOG.info("Failed to connect to switch.")
            raise ml2_except.MechanismDriverError()

    def bind_port(self, context):
        """Attempt to bind a port.

        :param context: PortContext instance describing the port

        Called outside any transaction to attempt to establish a port
        binding using this mechanism driver. If the driver is able to
        bind the port, it must call context.set_binding() with the
        binding details. If the binding results are committed after
        bind_port() returns, they will be seen by all mechanism
        drivers as update_port_precommit() and
        update_port_postcommit() calls.

        Note that if some other thread or process concurrently binds
        or updates the port, these binding results will not be
        committed, and update_port_precommit() and
        update_port_postcommit() will not be called on the mechanism
        drivers with these results. Because binding results can be
        discarded rather than committed, drivers should avoid making
        persistent state changes in bind_port(), or else must ensure
        that such state changes are eventually cleaned up.
        """
        
        LOG.debug("Attempting to bind port %(port)s on "
                  "network %(network)s",
                  {'port': context.current['id'],
                   'network': context.network.current['id']})

        for segment in context.network.network_segments:
            if self.check_segment(segment):
                context.set_binding(segment[driver_api.ID],
                                    self.vif_type,
                                    self.vif_details,
                                    status=neutron_const.PORT_STATUS_ACTIVE)
                LOG.debug("Bound using segment: %s", segment)
            else:
                LOG.debug("Refusing to bind port for segment ID %(id)s, "
                          "segment %(seg)s, phys net %(physnet)s, and "
                          "network type %(nettype)s",
                          {'id': segment[driver_api.ID],
                           'seg': segment[driver_api.SEGMENTATION_ID],
                           'physnet': segment[driver_api.PHYSICAL_NETWORK],
                           'nettype': segment[driver_api.NETWORK_TYPE]})
        
        context.host = context._binding.host
        LOG.debug("Bound using context.host: %s", context.host)

    def clear_database(self):
        """Delete any unnecessary entries in database."""
        db_all_user = get_all_tenant()
        for tenant in db_all_user:
            neutron_all_network = self.neutron_network_db.get_user_all_network(tenant)
            neutron_all_network_id = []
            for net in neutron_all_network:
                neutron_all_network_id.append(net['id'])
            db_all_network = get_all_network(tenant)
            for db_network_id in db_all_network.keys():
                if db_network_id not in neutron_all_network_id:
                    delete_network(tenant, db_network_id)


class HuaweiSwitchNeutronNetwork(db_base_plugin_v2.NeutronDbPluginV2):
    """Get Neutron network database table information.

    Provides access to the Neutron database for all provisioned
    networks as well ports. This data is used during the synchronization
    of database between ML2 Mechanism Driver and Huawei Switch
    Names of the networks and ports are not stroed in Huawei repository
    They are pulled from Neutron database.
    """

    def __init__(self):
        self.admin_context = neutron_context.get_admin_context()

    def get_user_all_network(self, tenant_id):
        """Get all Neutron network table information."""
        filters = {'tenant_id': [tenant_id]}
        return super(HuaweiSwitchNeutronNetwork,
                     self).get_networks(self.admin_context, filters=filters) or []


class HuaweiSwitchVlanBitmap(object):
    """Setup a VLAN bitmap for allocation or de-allocation."""
    
    def __init__(self, max):
        """Initialize the VLAN set."""
        self.size = self.get_array_location(max, True)
        self.array = [0 for i in range(self.size)]

    def format_into_string(self):
        """Format string."""
        sumstring = ''
        for i in self.array:
            string = struct.pack("!i", i)
            string = repr(string)[3:5] + repr(string)[7:9] + repr(string)[11:13] + repr(string)[15:17]
            sumstring = sumstring + string
        return sumstring

    def get_array_location(self, num, up=False):
        """Get array location."""
        return num / 32

    def get_bit_location(self, num):
        """Get bit location."""
        return num % 32

    def add_bitmap(self, num):
        """Add a bitmap."""
        elemIndex = self.get_array_location(num)
        print ("elemIndex=%d") % elemIndex
        byteIndex = self.get_bit_location(num)
        print ("byteIndex=%d") % byteIndex
        elem      = self.array[elemIndex]
        self.array[elemIndex] = elem | (1 << (31 - byteIndex))

    def delete_bitmap(self, num):
        """Delete a bitmap."""
        elemIndex = self.get_array_location(num)
        byteIndex = self.get_bit_location(num)
        elem      = self.array[elemIndex]
        self.array[elemIndex] = elem & (~(1 << (31 - byteIndex)))


class HuaweiSwitchConfigError(exceptions.NeutronException):
    """Mechanism driver call failed.
    
    The error information when Huawei switch is configured.
    """
    
    message = _('%(msg)s')

