..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Huawei Switch ML2 Mechanism driver
==================================

https://blueprints.launchpad.net/neutron/+spec/ml2-huawei-switch-mech-driver

This blueprint is to introduce support for Huawei switches in Neutron as a
ML2 mechanism driver.

Problem description
===================

This blueprint proposes Huawei's modular L2 mechanism driver to automate the
provisioning of physical Huawei switches (spine and leaf switches) based
on the virtual network configuration in OpenStack Neutron.


Proposed change
===============

The diagram below provides a brief overview of how the Huawei Switch ML2
Mechanism driver interact with Neutron Server and Huawei switches.
Flows::

          +–––––––––––––––––––––––––+
          |                         |
          | Neutron Server          |
          | with ML2 Plugin         |
          |                         |
          |       +–––––––––––––––––+
  +–––––––+       |                 |      
  |       |       |  Huawei Switch  +––––––––––––––––––––––+
  |       |       |   Mechanism     |      NETCONF         |
  |  +––––+       |    Driver       +––––––––––––––––––––––––––+
  |  |    |       |                 |                      |   |
  |  |    +–––––––+–––––––––––––––––+                      |   |
  |  |                                                     |   |
  |  |                                                     |   |
  |  |    +–––––––––––+––––––––––––––+                     |   |
  |  +––––+ L2 Agent  | Open vSwitch +–––––+               |   |
  |       +–––––––––––+––––––––––––––+     |               |   |
  |       |                          |     |               |   |
  |       |        HOST 1            |     |               |   |
  |       |                          |     |      +––––––––+–––|––––––+
  |       +––––––––––––––––––––––––––+     |      |            |      |
  |                                        +––––––+  +–––––––––+––––––+––+
  |                                               |  |                   |
  |       +––––––––––+–––––––––––––––+            |  |     Huawei        |
  +–––––––+ L2 Agent | Open vSwitch  +––––––––––––+  |    switches       |
          +––––––––––+–––––––––––––––+            |  |                   |
          |                          |            +––+                   |
          |        HOST 2            |               |                   |
          |                          |               +–––––––––––––––––––+
          +––––––––––––––––––––––––––+
		  
The APIC mechanism driver updates the APIC with port, network and
The Huawei Switch ML2 driver will implement CRUD APIs for network, subnets,
and ports. It configures the physical switch through NetConf protocol.

The Huawei Switch ML2 driver is deisgned to operate togehter with the OVS
mechanism driver or Linux bridge for handling network operation and port
binding on the compute nodes.

The following Neutron events are supported:

 * Network create/update/delete
 * Subnet  create/update/delete
 * Port    create/update/delete (Note: the driver does not handle port 
   bindingi -- the OVS driver or linux bridge driver already handle it.)

Supported network types include vlan and other types will be provided in
future.


Alternatives
------------

None

Data model impact
-----------------

This mechanism driver introduces three new tables which are specific to the
Huawei Switch mechanism driver.

 * huawei_switch_tenant: Stores tenant information.
 * huawei_switch_port: Stores between network and port configuration.
 * huawei_switch_network: Stores between network and network
   segmentation (VLAN) information

No existing models are changed.


REST API impact
---------------

None


Security impact
---------------

None


Notifications impact
--------------------

None


Other end user impact
---------------------

None


Performance Impact
------------------

None


Other deployer impact
---------------------

The deployer must configure the installation to use the Huawei Switch ML2
mechanism driver with the following configuration variables:

 * IP address of Huawei switches
 * Username and password to access Huawei switches' netconf agent
 * VLAN ranges to be used by OpenStack
 * Huawei switch with hosts mapping for the compute nodes

Additionally, the deployer must configure the ML2 plugin to include Huawei
Switch ML2 mechanism driver:

::

  [ml2]
  mechanism_drivers = openvswitch,huawei_switch


Developer impact
----------------

None


Implementation
==============

None


Assignee(s)
-----------

Primary assignee:

liaowenqi
yapengwu

Work Items
----------

Huawei Switch ML2 mechanism driver code
Unit tests
Huawei CI infrastructure with ML2 driver

Dependencies
============

None


Testing
=======

Unit Test coverage
Support for this driver in Huawei CI


Documentation Impact
====================

Huawei Switch ML2 Mechanism driver description and configuration details will
be added.


References
==========

https://wiki.openstack.org/wiki/Ml2-huawei-switch-mech-driver
