
Architecture
==================


High-Level overview
--------------------

This page provides an overview of the internal architecture of CTAM.  For detailed usage and new test creation,
refer to: :ref:`ctam_usage`


The primary organization is a TestSuite, which is just a collection of TestGroups.  test_runner.json provides for
multiple test suites to be defined, with only one being active at a time via the "active_test_suite" setting.

Interfaces do not contain any verification code but provide related functional API's to the device under test. SOLID
design principles should be used in the creation of interfaces to prevent monolithic collections of unrelated API's.
Inheritance patterns can work well when device configurations cause significant interface specialization.
Interfaces are only instantiated if a TestGroup requires it.  As Interfaces can have some overhead, that is why
they should only have a single responsibility to minimize startup and configuration for single TestCases or TestGroups.

TestGroups contain a collection of functionally related TestCases. Test groups have access to interfaces required for
the groups TestCases.  ExampleTestGroup has access to TelemetryInterface and ExampleInterface below.  The TestGroup
has a collection of TestCases.  Both the TestGroup and the group's TestCases have access to the Interfaces. The TestGroup
has both a setup() and teardown() function that may configure a system state prior to running all of the TestCases and
restore the state after all the TestCases in that group are completed.  Both are optional.

TestCases actually contain the verifiers to ensure compliance.  Each TestCase also has an optional setup() and teardown()
function.

.. mermaid::


    classDiagram

        class FunctionalIfc {
            +dut()
        }
        class FirmwareUpdateInterface
        class FirmwareUpdateDiscreteGpuInterface
        class FirmwareUpdateUbbGpuInterface
        class HealthCheckInterface
        class RasInterface
        class TelemetryInterface
        class ExampleInterface
        FunctionalIfc <|-- FirmwareUpdateInterface
        FunctionalIfc <|-- HealthCheckInterface
        FunctionalIfc <|-- RasInterface
        FunctionalIfc <|-- TelemetryInterface
        FunctionalIfc <|-- ExampleInterface
        FirmwareUpdateInterface <|-- FirmwareUpdateDiscreteGpuInterface
        FirmwareUpdateInterface <|-- FirmwareUpdateUbbGpuInterface

        class TestGroup {
            <<abstract>>
            +setup()*
            +teardown()*
            +dut()
            +test_run()
        }
        class TestCase {
            <<abstract>>
            +setup()*
            +teardown()*
            +run()*
            +dut()
            +test_run()
        }
        class TestSuite {
            not a real class
            list of groups obtained
            from active_test_suite
            in test_runner.json
        }
        TestGroup "1" -- "1..*" TestCase : contains List
        VerifyExampleTest --|> TestCase
        ExampleTestGroup --|> TestGroup
        TestSuite "1" -- "1..*" TestGroup : contains List
        ExampleTestGroup --> ExampleInterface: uses
        ExampleTestGroup --> TelemetryInterface: uses



Detailed documentation about the classes above can be found at:

- :class:`ctam.tests.test_group.TestGroup`
- :class:`ctam.tests.test_case.TestCase`
- :class:`ctam.interfaces.Functional_Ifc.FunctionalIfc`



Internal Structure
--------------------

Following are details that are not required for creating tests but are useful for internal configuration.
Most of the associations between these classes are via python class attributes as they are singletons.  This allows
the framework to make the association once, but all of the subclass instances have access to the singleton objects.
The connections are made externally to the classes, which allows for mock classes to be injected for internal testing.
Interfaces have access to the Dut object, while TestGroups and TestCases have access to the Dut, and TestRun objects.

.. mermaid::


    classDiagram

        class FunctionalIfc

        class TestGroup {
            <<abstract>>
            +setup()*
            +teardown()*
            +dut()
            +test_run()
        }
        class TestCase {
            <<abstract>>
            +setup()*
            +teardown()*
            +run()*
            +dut()
            +test_run()
        }
        class TestSuite {
            not a real class
            list of groups obtained
            from active_test_suite
            in test_runner.json
        }
        class ocptv_dut
        class ocptv_TestRun
        ocptv_dut <|-- CompToolDut
        TestGroup "1" -- "1..*" TestCase : contains List
        TestSuite "1" -- "1..*" TestGroup : contains List
        FunctionalIfc --> CompToolDut: uses via class attrib
        TestGroup --> CompToolDut: uses via class attrib
        TestCase --> CompToolDut: uses via class attrib
        TestCase --> ocptv_TestRun: uses via class attrib
        TestGroup --> ocptv_TestRun: uses via class attrib
        CompToolDut *-- UriBuilder
        TestHierarchy "1" -- "1..*" TestGroup : contains List
        TestRunner --> TestHierarchy: uses
        TestRunner --> TestSuite: uses



Detailed documentation about the classes above can be found at:

- :class:`ctam.test_hierarchy.TestHierarchy`
- :class:`ctam.test_runner.TestRunner`
- :class:`ctam.interfaces.Functional_Ifc.FunctionalIfc`
- :class:`ctam.interfaces.comptool_dut.CompToolDut`
- :class:`ctam.interfaces.uri_builder.UriBuilder`
- :class:`ctam.tests.test_group.TestGroup`
- :class:`ctam.tests.test_case.TestCase`

Run-time Execution
--------------------

This diagram just shows that main starts up, instantiates TestHierarchy, walks the Test directory tree and populates
lists of TestGroups and related TestCases.  Main then instantiates TestRunner with options from the Workspace directory
which then proceeds to run the TestSuite.

.. mermaid::


    classDiagram
        Main -- TestHierarchy: instantiates
        Main -- TestRunner: instantiates
        class TestHierarchy
        class TestRunner
        class Main {
            note: Represents main.py
        }



TestSuite Execution
--------------------

This sequenceDiagram shows how TestGroup, TestCase setup and teardowns are sequenced.

.. mermaid::

    sequenceDiagram
        participant TestRunner
        participant TestGroup
        participant TestCase
        loop for each TestGroup in TestSuite
            TestRunner->>TestGroup: setup()
            loop for each TestCase in TestGroup
                TestRunner->>TestCase: setup()
                TestRunner->>TestCase: run()
                TestCase->>TestGroup: call TestGroup's Interfaces
                TestCase -->> TestRunner: complete(pass/fail)
                TestRunner->>TestCase: teardown()
            end
            TestRunner->>TestGroup: teardown()
        end


Example TestLog showing sequencing
    .. code::

        {"schemaVersion": {"major": 2, "minor": 0}, "sequenceNumber": 0, "timestamp": "2023-06-18T15:19:28.138167Z"}
        {"testRunArtifact": {"testRunStart": {"name": "act", "version": "1.0", "commandLine": "-w C:\\comptool\\gh-act/example_workspace", "parameters": {}, "dutInfo": {"dutInfoId": "dut0", "platformInfos": [], "softwareInfos": [], "hardwareInfos": []}}}, "sequenceNumber": 1, "timestamp": "2023-06-18T15:19:28.141224Z"}
        {"testStepArtifact": {"testStepId": "0", "testStepStart": {"name": "TestGroup.setup()..."}}, "sequenceNumber": 2, "timestamp": "2023-06-18T15:19:28.142745Z"}
        {"testStepArtifact": {"testStepId": "0", "testStepEnd": {"status": "COMPLETE"}}, "sequenceNumber": 3, "timestamp": "2023-06-18T15:19:28.143748Z"}
        {"testStepArtifact": {"testStepId": "1", "testStepStart": {"name": "BasicHealthCheckTestGroup  setup()..."}}, "sequenceNumber": 4, "timestamp": "2023-06-18T15:19:28.144746Z"}
        {"testStepArtifact": {"testStepId": "1", "testStepEnd": {"status": "COMPLETE"}}, "sequenceNumber": 5, "timestamp": "2023-06-18T15:19:28.145746Z"}
        {"testStepArtifact": {"testStepId": "2", "testStepStart": {"name": "TestCase.setup()..."}}, "sequenceNumber": 6, "timestamp": "2023-06-18T15:19:28.146747Z"}
        {"testStepArtifact": {"testStepId": "2", "testStepEnd": {"status": "COMPLETE"}}, "sequenceNumber": 7, "timestamp": "2023-06-18T15:19:28.147745Z"}
        {"testStepArtifact": {"testStepId": "3", "testStepStart": {"name": "VerifyExampleTest  setup()..."}}, "sequenceNumber": 8, "timestamp": "2023-06-18T15:19:28.147745Z"}
        {"testStepArtifact": {"testStepId": "3", "testStepEnd": {"status": "COMPLETE"}}, "sequenceNumber": 9, "timestamp": "2023-06-18T15:19:28.148748Z"}
        {"testStepArtifact": {"testStepId": "4", "testStepStart": {"name": "VerifyExampleTest run(), step1"}}, "sequenceNumber": 10, "timestamp": "2023-06-18T15:19:28.149746Z"}
        {"testStepArtifact": {"testStepId": "4", "testStepEnd": {"status": "COMPLETE"}}, "sequenceNumber": 11, "timestamp": "2023-06-18T15:19:28.151749Z"}
        {"testStepArtifact": {"testStepId": "5", "testStepStart": {"name": "VerifyExampleTest step2"}}, "sequenceNumber": 12, "timestamp": "2023-06-18T15:19:28.151749Z"}
        {"testRunArtifact": {"log": {"severity": "DEBUG", "message": "Example Debug message in VerifyExampleTest", "sourceLocation": {"file": "C:\\comptool\\gh-act\\ctam\\tests\\health_check\\basic_health_check_group\\verify_example_test.py", "line": 65}}}, "sequenceNumber": 13, "timestamp": "2023-06-18T15:19:28.261847Z"}
        {"testStepArtifact": {"testStepId": "5", "testStepEnd": {"status": "COMPLETE"}}, "sequenceNumber": 14, "timestamp": "2023-06-18T15:19:28.264849Z"}
        {"testStepArtifact": {"testStepId": "6", "testStepStart": {"name": "VerifyExampleTest  teardown()..."}}, "sequenceNumber": 15, "timestamp": "2023-06-18T15:19:28.265849Z"}
        {"testStepArtifact": {"testStepId": "6", "testStepEnd": {"status": "COMPLETE"}}, "sequenceNumber": 16, "timestamp": "2023-06-18T15:19:28.268847Z"}
        {"testStepArtifact": {"testStepId": "7", "testStepStart": {"name": "TestCase.teardown()..."}}, "sequenceNumber": 17, "timestamp": "2023-06-18T15:19:28.271846Z"}
        {"testStepArtifact": {"testStepId": "7", "testStepEnd": {"status": "COMPLETE"}}, "sequenceNumber": 18, "timestamp": "2023-06-18T15:19:28.273850Z"}
        {"testStepArtifact": {"testStepId": "8", "testStepStart": {"name": "TestCase.setup()..."}}, "sequenceNumber": 19, "timestamp": "2023-06-18T15:19:28.275850Z"}
        {"testStepArtifact": {"testStepId": "8", "testStepEnd": {"status": "COMPLETE"}}, "sequenceNumber": 20, "timestamp": "2023-06-18T15:19:28.278845Z"}
        {"testStepArtifact": {"testStepId": "9", "testStepStart": {"name": "VerifyRedfishSoftwareInventoryCollection  setup()..."}}, "sequenceNumber": 21, "timestamp": "2023-06-18T15:19:28.280845Z"}
        {"testStepArtifact": {"testStepId": "9", "testStepEnd": {"status": "COMPLETE"}}, "sequenceNumber": 22, "timestamp": "2023-06-18T15:19:28.282843Z"}
        {"testStepArtifact": {"testStepId": "10", "testStepStart": {"name": "VerifyRedfishSoftwareInventoryCollection run(), step1"}}, "sequenceNumber": 23, "timestamp": "2023-06-18T15:19:28.285844Z"}
        {"testStepArtifact": {"testStepId": "10", "testStepEnd": {"status": "COMPLETE"}}, "sequenceNumber": 24, "timestamp": "2023-06-18T15:19:34.719081Z"}
        {"testStepArtifact": {"testStepId": "11", "testStepStart": {"name": "VerifyRedfishSoftwareInventoryCollection step2"}}, "sequenceNumber": 25, "timestamp": "2023-06-18T15:19:34.721087Z"}
        {"testRunArtifact": {"log": {"severity": "DEBUG", "message": "Debug mode is True in VerifyRedfishSoftwareInventoryCollection", "sourceLocation": {"file": "C:\\comptool\\gh-act\\ctam\\tests\\health_check\\basic_health_check_group\\verify_redfish_software_inventory_collection.py", "line": 64}}}, "sequenceNumber": 26, "timestamp": "2023-06-18T15:19:34.724090Z"}
        {"testStepArtifact": {"testStepId": "11", "testStepEnd": {"status": "COMPLETE"}}, "sequenceNumber": 27, "timestamp": "2023-06-18T15:19:34.725089Z"}
        {"testStepArtifact": {"testStepId": "12", "testStepStart": {"name": "VerifyRedfishSoftwareInventoryCollection  teardown()..."}}, "sequenceNumber": 28, "timestamp": "2023-06-18T15:19:34.727091Z"}
        {"testStepArtifact": {"testStepId": "12", "testStepEnd": {"status": "COMPLETE"}}, "sequenceNumber": 29, "timestamp": "2023-06-18T15:19:34.728088Z"}
        {"testStepArtifact": {"testStepId": "13", "testStepStart": {"name": "TestCase.teardown()..."}}, "sequenceNumber": 30, "timestamp": "2023-06-18T15:19:34.728088Z"}
        {"testStepArtifact": {"testStepId": "13", "testStepEnd": {"status": "COMPLETE"}}, "sequenceNumber": 31, "timestamp": "2023-06-18T15:19:34.729088Z"}
        {"testRunArtifact": {"log": {"severity": "INFO", "message": "Compliance Run completed. Total Score = 20.00 out of 20.00, Grade = 100.00%", "sourceLocation": {"file": "C:\\comptool\\gh-act\\ctam\\test_runner.py", "line": 280}}}, "sequenceNumber": 32, "timestamp": "2023-06-18T15:19:34.731090Z"}
        {"testStepArtifact": {"testStepId": "14", "testStepStart": {"name": "BasicHealthCheckTestGroup  teardown()..."}}, "sequenceNumber": 33, "timestamp": "2023-06-18T15:19:34.732088Z"}
        {"testStepArtifact": {"testStepId": "14", "testStepEnd": {"status": "COMPLETE"}}, "sequenceNumber": 34, "timestamp": "2023-06-18T15:19:34.733091Z"}
        {"testStepArtifact": {"testStepId": "15", "testStepStart": {"name": "TestGroup.teardown()..."}}, "sequenceNumber": 35, "timestamp": "2023-06-18T15:19:34.734595Z"}
        {"testStepArtifact": {"testStepId": "15", "testStepEnd": {"status": "COMPLETE"}}, "sequenceNumber": 36, "timestamp": "2023-06-18T15:19:34.735605Z"}
        {"testRunArtifact": {"testRunEnd": {"status": "COMPLETE", "result": "PASS"}}, "sequenceNumber": 37, "timestamp": "2023-06-18T15:19:34.737605Z"}









