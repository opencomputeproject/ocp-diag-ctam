.. _ctam_usage:

Usage
==================

Set-up
------------------------

- Pre-requisites for using SSH tunneling to connect to HMC:

    #. Install sshpass. In Ubuntu machine, run the following:
        ``sudo apt-get install python3-tk sshpass``        
    #. Enable port-forwarding in HostBMC.
        
        1. On the HostBmc, there is file /etc/ssh/sshd_config. In this file, set the AllowTcpForwarding to yes.
        2. Now restart the ssh service with following cmd:
                ``/etc/init.d/ssh restart``

Command Line options
------------------------

There are a few command line options. refer to    :func:`ctam.main.parse_args`

-w, --workspace is always required except for listing the Test Groups and Test classes.
The workspace is a directory that contains files necessary for the TestRun.  The workspace is stored outside of
this repo, however, directory /example_workspace is provided as a template to copy for actual workspaces.

-t option may be used to run a single test TestCase

-g option may be used to run a single TestGroup

otherwise the TestRun is based on the suite listed in test_runner.json in the workspace directory

Note: The framework auto discovers TestGroups and TestCases in the /test directory.  Newly created TestGroups and
TestCases will be immediately available for execution without any further configuration.

test_runner.json options
------------------------

- "output_override_directory": ""   Default test log directory is in a TestRuns directory under the workspace. Use this to customize location.
- "debug_mode": true    When true, enables debug logging, otherwise LogSeverity.DEBUG messages are filtered.
- "console_log": true  When true, prints test logging to stdout as well as file log.
- "include_tags": []   Include and Exclude tags are applied at the TestGroup level first. If the TestGroup is enabled, then the tags will be applied to each test case. For specific logic refer to:  :class:`ctam.test_runner.TestRunner._is_enabled`
- "exclude_tags": []  See above for include_tags
- "test_cases": []   Allows for a debugging sequence of individual TestCases
- "active_test_suite": "dev_test_suite"  The json file can list any number of TestSuites, this value is used to select one of them.
- "dev_test_suite": ["BasicHealthCheckTestGroup" ]  This is just an example TestSuite that only has a single TestGroup


Adding a new TestCase
------------------------

Adding new TestCases to existing groups will be the most common action.

-  Determine which TestGroup the TestCase belongs in.
-  In the directory of the TestGroup, create a new .py file.  The name of the file should be the name of the test in underscore case.
-  Open the file in VS Code and type 'ctam-testcase'  This will stub out the main contents of the TestCase and the snippet will create the TestCase class name as Pascal case.
-  update 'from <<TODO group module>> import <<TODO group class>>'  The group module will be the only test group file in the directory and the class will be Pascal case of the file.
-  update 'def __init__(self, group: <<TODO group class>>):' Use the TestGroup class name
-  Update 'test_id', 'score_weight', 'include_tags', 'exclude_tags'
-  Update documentation 'TODO'
-  The TestCase is now executable, can verify via the -t command line option.

TestCase Capabilities

-  Access TestGroup interfaces.
    -  Use VS Code intellisense or inspect TestGroup class in the group folder.  (Ex)
        .. code:: python

            self.group.health_check_ifc.get_software_inventory()

-  Add a test step (Ex)
     .. code:: python

        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")
        with step1.scope():
            self.group.health_check_ifc.get_software_inventory()

-  Access the Dut.
    -  Preferable to use Interfaces, but can access Dut directly from a TestCase if need be.  (Ex)
        .. code:: python

            debug_mode = self.dut().is_debug_mode()

-  Send a redfish message to the Dut.
    -  Due to configuration variances in redfish uri's, uri_builder is used to isolate the deltas in one location. Refer to :class:`ctam.interfaces.uri_builder.UriBuilder` for details.
        .. code:: python

               v1_str = self.dut().uri_builder.format_uri("{gpu_prefix}redfish/v1/")
               response = self.dut().redfish_ifc.get(v1_str)
               print(response.is_processing)
               print(response.status)
               print(response.task_location)
               print(response.dict)   #dictionary from returned json data

-  Add logging messages.
    -  Refer to OCP LogSeverity for available severities.
    -  LogSeverity.DEBUG messages will NOT be logged if "debug_mode" is false in test_runner.json
        .. code:: python

            debug_mode = self.dut().is_debug_mode()
            msg = f"Debug mode is {debug_mode} in {self.__class__.__name__}"
            self.test_run().add_log(severity=LogSeverity.DEBUG, message=msg)



Adding a new TestGroup
------------------------

Defining the granularity of TestGroup partitioning is important to the longer term execution and maintenance of the
compliance tool. As compliance failures are found, the user is likely to iterate on a single failing TestCase until
the issue is resolved and the TestCase passes. At the point, the next likely step is to re-run the TestGroup that the
failing TestCase is a part of. This will provide localized regression confidence that the fix did not
cause failures to related functionality. If the group tests succeed, then it will be read for a full TestSuite re-run.

These are the primary considerations when defining the scope of a TestGroup.  All are necessary to ensure the compliance
tool remains scalable, extensible and maintainable in the future.

-  Only group together related functionality.
-  Split large monolithic groups into multiple smaller groups.
-  Organize based on TestGroup setup() requirements.
    -   The TestGroup setup() function is used to place the system in a state(s) required by all TestCases in the group.
    -   The TestGroup teardown() function is used to undo the state(s) introduced by the setup() function.
    -   Many TestGroup's will not require any setup() or teardown().  The default handlers can be left for future requirements.

Determine the scope of the TestGroup based on criteria above

-  Create a new test group directory in the appropriate file hierarchy.
-  In the new directory, create a new .py file.  The name of the file should be the name of the test group in underscore case.
-  Open the file in VS Code and type 'ctam-testgroup'  This will stub out the main contents of the TestGroup and the snippet will create the TestGroup class name as Pascal case.
-  update 'from interfaces.<<TODO interface module>> import <<TODO interface class>>'  Add additional interfaces as needed.
-  update 'def configure_interfaces(self, <<TODO param name, ie hc_ifc>>: <<TODO interface class>>):' Add a parameter for each interface added above.
-  update '<<TODO assign all param interfaces to class variables for use by test cases ie self.health_check_ifc = hc_ifc>>' for all Interfaces'
-  Update  'include_tags', 'exclude_tags'
-  Update documentation 'TODO'
-  The TestGroup is now executable, can verify via the -g command line option.

TestGroup setup() / teardown() Capabilities

-  Access interfaces.
    -  Use VS Code intellisense or inspect TestGroup class in the group folder.  (Ex)
        .. code:: python

            self.health_check_ifc.get_software_inventory()

-  Add a test step (Ex)
     .. code:: python

        step1 = self.test_run().add_step(f"{self.__class__.__name__} run(), step1")
        with step1.scope():
            self.health_check_ifc.get_software_inventory()

-  Access the Dut.
    -  Preferable to use Interfaces, but can access Dut directly from a TestGroup if need be.  (Ex)
        .. code:: python

            debug_mode = self.dut().is_debug_mode()

-  Send a redfish message to the Dut.
    -  Due to configuration variances in redfish uri's, uri_builder is used to isolate the deltas in one location. Refer to :class:`ctam.interfaces.uri_builder.UriBuilder` for details.
        .. code:: python

               v1_str = self.dut().uri_builder.format_uri("{gpu_prefix}redfish/v1/")
               response = self.dut().redfish_ifc.get(v1_str)
               print(response.is_processing)
               print(response.status)
               print(response.task_location)
               print(response.dict)   #dictionary from returned json data

-  Add logging messages.
    -  Refer to OCP LogSeverity for available severities.
    -  LogSeverity.DEBUG messages will NOT be logged if "debug_mode" is false in test_runner.json
        .. code:: python

            debug_mode = self.dut().is_debug_mode()
            msg = f"Debug mode is {debug_mode} in {self.__class__.__name__}"
            self.test_run().add_log(severity=LogSeverity.DEBUG, message=msg)



Adding a new Interface
------------------------

Determine the scope of the Interface based on criteria above

-  In the interfaces directory, create a new .py file.  The name of the file should be the name of the interface in underscore case.
-  Open the file in VS Code and type 'ctam-interface'  This will stub out the main contents of the Interface and the snippet will create the Interface class name as Pascal case.
-  Update documentation 'TODO'
-  The Interface is now available.  Public api's can now be created that access self.dut().


Interface Capabilities

Interfaces do not have access to the TestRunner by design.  Interface API's should be kept short and perhaps compiled

-  Send a redfish message to the Dut.
    -  Due to configuration variances in redfish uri's, uri_builder is used to isolate the deltas in one location. Refer to :class:`ctam.interfaces.uri_builder.UriBuilder` for details.
        .. code:: python

               v1_str = self.dut().uri_builder.format_uri("{gpu_prefix}redfish/v1/")
               response = self.dut().redfish_ifc.get(v1_str)
               print(response.is_processing)
               print(response.status)
               print(response.task_location)
               print(response.dict)   #dictionary from returned json data