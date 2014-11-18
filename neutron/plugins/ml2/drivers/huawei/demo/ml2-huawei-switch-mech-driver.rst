..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Huawei CloudEngine ML2 mechanism driver
==========================================

https://blueprints.launchpad.net/neutron/+spec/ml2-huawei-switch-mech-driver

* HW-SDN MD : Huawei SDN Mechanism Driver
* HW-SDN CR : Huawei SDN Controller

The purpose of this blueprint is to build an ML2 Mechanism Driver for Huawei
CloundEngine switch, which provides NETCONF access ability for ML2 plugin of 
Neutron.

Problem description
===================

This blueprint specifies need of Huawei modular L2 mechanism driver to automate the provisioning of Huawei's CloudEngine Switch switches using NETCONF.

In current Openstack neutron deployment VM＊s attached to the overlay network could not communicate to the network devices/bare-metal 
servers attached to the physical networks. In addition, forwarding performance using software switch like Open vSwitch will be still
a problem in most scenes.


Proposed change
===============

The diagram below provides a high level overview of the interactions between Huawei CloudEngine switch and OpenStack components.

        +每每每每每每每每每每每每每每每每每每每每每每每每每+
        |                         |
        | Neutron Server          |
        | with ML2 Plugin         |
        |                         |
        |          +每每每每每每每每每每每+  |
+每每每每每每每+          |   Huawei  |  |
|       |          |CloudEngine|  |                  +每每每每每每每每每每每每每每每每每+
|       |          | Mechanism |  |                  |                 |
|  +----|          |  Driver   |  |                  |                 |
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
+每每每每每每每+ L2 Agent | Open vSwitch  +每每每每每每每每每每每每+  |    CloudEgine     |
        +每每每每每每每每每每+每每每每每每每每每每每每每每每+            |  |    Switches       |
        |                          |            +每每+                   |
        |        HOST 2            |               |                   |
        |                          |               +每每每每每每每每每每每每每每每每每每每+
        +每每每每每每每每每每每每每每每每每每每每每每每每每每+

The Huawei CloudEngine mechanism driver will handle the network events and configure CloudEngine switch using these data. 
This can be responsible for network between all the compute nodes.

When baremental or hypervisor with virtual machines connect to CloudEngine switch, the topology of physical network will be created. 
That means when you get ip of one host, the device and the port which the host connect to are fixed. So when users created network 
for compute nodes, mechanism driver can handle vlan information with specific port on corresponding device.


Huawei Mechanism driver handles the following postcommit operations.

Network create/update/delete
Subnet  create/update/delete
Port    create/delete

Supported network types include vlan and other types will be provided in future.


Alternatives
------------

None

Data model impact
-----------------

This mechanism driver introduces new table which are specific to the Huawei CloudEngine mechanism driver.

Networktopology: Stores binding between host and port, device

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

Additionally, the deployer must configure the ML2 plugin to include the openvswitch mechanism driver before the Huawei CloudEngine mechanism driver:

[ml2]
mechanism_drivers = linuxbridge,ml2-huawei-switch-mech-driver



Developer impact
----------------

None

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  xieyinqiao

Work Items
----------

1. Change the setup.cfg to introduce 'huawei' as the mechanism driver.
2. An REST client for SDN controller should be developed first.
3. Mechanism driver should implement create/update/delete_resource_postcommit.
4. Test connection between two new instances under different subnets.

Dependencies
============

None

Testing
=======

1. The whole setup can be deployed using OVS and SDN controller can be deployed
in VM.
2. For each module added to the mechanism driver, unit test is provided.
3. Functional testing with tempest will be provided. The third-party Huawei CI
report will be provided to validate this ML2 mechanism driver.

Documentation Impact
====================

Huawei SDN mechanism driver description and configuration details will be added.

References
==========

https://review.openstack.org/#/c/68148/


