..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Huawei Switch ML2 Mechanism driver
==========================================

https://blueprints.launchpad.net/neutron/+spec/ml2-huawei-switch-mech-driver

* HW-SDN MD : Huawei Switch Mechanism Driver
* HW-SDN CR : Huawei Switch

The purpose of this blueprint is to build an ML2 Mechanism Driver for Huawei
Switch, which provides NETCONF access ability for ML2 plugin of Neutron.

Problem description
===================

This blueprint specifies need of Huawei Switch ML2 Mechanism driver to automate the provisioning of Huawei Switch using NETCONF.

In current Openstack Neutron deployment VM＊s attached to the overlay network could not communicate to the network devices/bare-metal 
servers attached to the physical networks. In addition, forwarding performance using software switch like Open vSwitch will be still
a problem in most scenes.


Proposed change
===============

The diagram below provides a high level overview of the interactions between Huawei Switch and OpenStack components.

        +每每每每每每每每每每每每每每每每每每每每每每每每每+
        |                         |
        | Neutron Server          |
        | with ML2 Plugin         |
        |                         |
        |          +每每每每每每每每每每每+  |
+每每每每每每每+          |   Huawei  |  |
|       |          |   Switch  |  |                  +每每每每每每每每每每每每每每每每每+
|       |          |   ML2     |  |                  |                 |
|  +----|          |   Driver  |  |                  |                 |
|  |    |          +-----------+  |+每每每每每每每每每每每每每每每每每|     NETCONF     |
|  |    +每每每每每每每+每每每每每每每每每每每每每每每每每+                  |                 |
|  |                                                 |                 |
|  |                                                 +每每每+每每每+每每每每每每每每每+
|  |    +每每每每每每每每每每每+每每每每每每每每每每每每每每+                     |   |
|  +每每每每+ L2 Agent  | Open vSwitch +每每每每每+               |   |
|       +每每每每每每每每每每每+每每每每每每每每每每每每每每+     |               |   |
|       |                          |     |               |   |
|       |        HOST 1            |     |               |   |
|       |                          |     |      +每每每每每每每每+每每每|每每每每每每+
|       +每每每每每每每每每每每每每每每每每每每每每每每每每每+     |      |            |      |
|                                        +每每每每每每+  +每每每每每每每每每+每每每每每每+每每+
|                                               |  |                   |
|       +每每每每每每每每每每+每每每每每每每每每每每每每每每+            |  |     Huawei        |
+每每每每每每每+ L2 Agent | Open vSwitch  +每每每每每每每每每每每每+  |     Switch        |
        +每每每每每每每每每每+每每每每每每每每每每每每每每每+            |  |                   |
        |                          |            +每每+                   |
        |        HOST 2            |               |                   |
        |                          |               +每每每每每每每每每每每每每每每每每每每+
        +每每每每每每每每每每每每每每每每每每每每每每每每每每+

The Huawei Switch ML2 driver will handle the network events and configure Huawei Switch using these data. 
This can be responsible for network between all the compute nodes.

When baremental or hypervisor with virtual machines connect to Huawei Switch, the topology of physical network will be created. 
That means when you get IP address of one host, the device and the port which the host connect to are fixed. So when users created network 
for compute nodes, the ML2 Mechanism driver can handle vlan information with specific port on corresponding device.


Huawei Switch ML2 driver handles the following postcommit operations.

Network create/update/delete
Subnet  create/update/delete
Port    create/update/delete

Supported network types include vlan and other types will be provided in future.


Alternatives
------------

None


Data model impact
-----------------

This mechanism driver introduces new table which are specific to the Huawei Switch mechanism driver.

Network topology: Stores binding between host and port, device

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

None



Developer impact
----------------

None


Implementation
==============

None


Assignee(s)
-----------

Primary assignee:

None


Work Items
----------

1. Change the setup.cfg to introduce 'huawei' as the mechanism driver.
2. An REST client for Huawei Switch should be developed first.
3. Mechanism driver should implement create/update/delete_resource_postcommit.
4. Test connection between two new instances under different subnets.


Dependencies
============

None


Testing
=======

1. The whole setup can be deployed using OVS and Huawei Switch can be deployed
in VM.
2. For each module added to the mechanism driver, unit test is provided.
3. Functional testing with tempest will be provided. The third-party Huawei CI
report will be provided to validate this ML2 mechanism driver.


Documentation Impact
====================

Huawei Switch ML2 Mechanism driver description and configuration details will be added.


References
==========

https://wiki.openstack.org/wiki/Ml2-huawei-switch-mech-driver

